// SPDX-FileCopyrightText: 2026 Artur <ganggg111@gmail.com>
// SPDX-License-Identifier: MIT
//
// Window thumbnails for the shell's task switcher.  The hwcomposer output
// cannot be read back from outside the compositor (screencopy gives a white
// image), so the view is rendered here with take_snapshot(), shrunk on the
// CPU and written as a binary PPM that Qt loads without extra plugins.
//
// IPC: podglad/capture {"view-id": N, "file": "/run/user/.../x.ppm",
//                       "scale": 2}  ->  {"result": "ok", "width", "height"}
// Based on view-shot from wayfire-plugins-extra (MIT, Scott Moreau).
//
// Also keeps maximized windows full size.  place maximizes a window only
// after it maps, and the client's first commit at its own default size can
// land after that and win: the toplevel stays tiled on all edges but at
// e.g. 360x720 (kclock) instead of the 480x946 workarea, in about two of
// three launches of Qt apps.  Such a window gets the tile request again.
//
// IPC: podglad/volume-keys {"app-id": "...", "enabled": true|false}.  While a
// window of a registered app is active, the volume keys do not reach the
// compositor at all (no amixer bindings, no client).  The camera reads them
// from the evdev device as its shutter.  A registration ends with the client's
// connection.

#include <wayfire/core.hpp>
#include <wayfire/nonstd/wlroots-full.hpp>
#include <wayfire/opengl.hpp>
#include <wayfire/seat.hpp>
#include <wayfire/output.hpp>
#include <wayfire/plugin.hpp>
#include <wayfire/signal-definitions.hpp>
#include <wayfire/toplevel-view.hpp>
#include <wayfire/util.hpp>
#include <wayfire/view.hpp>
#include <wayfire/window-manager.hpp>
#include <wayfire/workarea.hpp>
#include <wayfire/plugins/common/shared-core-data.hpp>
#include <wayfire/plugins/ipc/ipc-helpers.hpp>
#include <wayfire/plugins/ipc/ipc-method-repository.hpp>

#include <linux/input-event-codes.h>

#include <cstdio>
#include <map>
#include <set>
#include <string>
#include <vector>

class wayfire_podglad : public wf::plugin_interface_t
{
    wf::shared_data::ref_ptr_t<wf::ipc::method_repository_t> ipc_repo;

    // retries per view, so a client that refuses the size cannot loop
    static constexpr int MAX_RETRIES = 3;
    std::map<uint32_t, int> retries;
    std::set<uint32_t> to_retile;
    wf::wl_idle_call idle_retile;

    // app-id -> IPC client that asked for the volume keys
    std::map<std::string, wf::ipc::client_interface_t*> volume_key_apps;

  public:
    void init() override
    {
        ipc_repo->register_method("podglad/capture", on_capture);
        ipc_repo->register_method("podglad/volume-keys", on_volume_keys);
        ipc_repo->connect(&on_client_disconnected);
        wf::get_core().connect(&on_mapped);
        wf::get_core().connect(&on_geometry);
        wf::get_core().connect(&on_key);
    }

    void fini() override
    {
        ipc_repo->unregister_method("podglad/capture");
        ipc_repo->unregister_method("podglad/volume-keys");
        on_client_disconnected.disconnect();
        on_mapped.disconnect();
        on_geometry.disconnect();
        on_key.disconnect();
        idle_retile.disconnect();
    }

    wf::ipc::method_callback_full on_volume_keys =
        [=] (nlohmann::json data, wf::ipc::client_interface_t *client)
    {
        WFJSON_EXPECT_FIELD(data, "app-id", string);
        WFJSON_EXPECT_FIELD(data, "enabled", boolean);
        const std::string app_id = data["app-id"];
        if (data["enabled"])
        {
            volume_key_apps[app_id] = client;
        } else
        {
            volume_key_apps.erase(app_id);
        }

        return wf::ipc::json_ok();
    };

    wf::signal::connection_t<wf::ipc::client_disconnected_signal> on_client_disconnected =
        [=] (wf::ipc::client_disconnected_signal *ev)
    {
        for (auto it = volume_key_apps.begin(); it != volume_key_apps.end();)
        {
            it = (it->second == ev->client) ? volume_key_apps.erase(it) : std::next(it);
        }
    };

    wf::signal::connection_t<wf::input_event_signal<wlr_keyboard_key_event>> on_key =
        [=] (wf::input_event_signal<wlr_keyboard_key_event> *ev)
    {
        const uint32_t key = ev->event->keycode;
        if ((key != KEY_VOLUMEUP) && (key != KEY_VOLUMEDOWN))
        {
            return;
        }

        // a release follows its press, whatever has the focus by then, so a
        // repeating binding can never be left running
        if (ev->event->state == WL_KEYBOARD_KEY_STATE_RELEASED)
        {
            if (swallowed.erase(key))
            {
                ev->mode = wf::input_event_processing_mode_t::IGNORE;
            }

            return;
        }

        auto view = wf::get_core().seat->get_active_view();
        if (view && volume_key_apps.count(view->get_app_id()))
        {
            swallowed.insert(key);
            ev->mode = wf::input_event_processing_mode_t::IGNORE;
        }
    };

    std::set<uint32_t> swallowed;

    wf::signal::connection_t<wf::view_mapped_signal> on_mapped =
        [=] (wf::view_mapped_signal *ev)
    {
        check_maximized(wf::toplevel_cast(ev->view));
    };

    wf::signal::connection_t<wf::view_geometry_changed_signal> on_geometry =
        [=] (wf::view_geometry_changed_signal *ev)
    {
        check_maximized(ev->view);
    };

    void check_maximized(wayfire_toplevel_view view)
    {
        if (!view || !view->is_mapped() || view->parent ||
            (view->role != wf::VIEW_ROLE_TOPLEVEL) || !view->get_output())
        {
            return;
        }

        const auto& state = view->toplevel()->pending();
        if ((state.tiled_edges != wf::TILED_EDGES_ALL) || state.fullscreen)
        {
            return;
        }

        const uint32_t id = view->get_id();
        if (state.geometry == view->get_output()->workarea->get_workarea())
        {
            retries.erase(id);
            return;
        }

        if (retries[id]++ >= MAX_RETRIES)
        {
            return;
        }

        // not from inside the signal: the size change is still being applied
        to_retile.insert(id);
        idle_retile.run_once([=] ()
        {
            auto ids = std::move(to_retile);
            to_retile.clear();
            for (auto id : ids)
            {
                auto v = wf::toplevel_cast(wf::ipc::find_view_by_id(id));
                if (v && v->is_mapped())
                {
                    wf::get_core().default_wm->tile_request(v, wf::TILED_EDGES_ALL);
                }
            }
        });
    }

    wf::ipc::method_callback on_capture = [=] (nlohmann::json data)
    {
        WFJSON_EXPECT_FIELD(data, "view-id", number_unsigned);
        WFJSON_EXPECT_FIELD(data, "file", string);
        int scale = 2;
        if (data.contains("scale") && data["scale"].is_number_unsigned())
        {
            scale = std::max(1, std::min(8, (int)data["scale"]));
        }

        auto view = wf::ipc::find_view_by_id(data["view-id"]);
        if (!view || !view->is_mapped())
        {
            return wf::ipc::json_error("No such view found!");
        }

        int width = 0, height = 0;
        if (!capture(view, data["file"], scale, width, height))
        {
            return wf::ipc::json_error("Failed to capture view.");
        }

        // the shell reads replies asynchronously, so say which view it was
        auto reply = wf::ipc::json_ok();
        reply["podglad"] = data["view-id"];
        reply["file"]    = data["file"];
        reply["width"]   = width;
        reply["height"] = height;
        return reply;
    };

    bool capture(wayfire_view view, const std::string& file, int scale,
        int& out_w, int& out_h)
    {
        wf::render_target_t buffer;
        view->take_snapshot(buffer);
        const int w = buffer.viewport_width;
        const int h = buffer.viewport_height;
        if ((w <= 0) || (h <= 0))
        {
            OpenGL::render_begin();
            buffer.release();
            OpenGL::render_end();
            return false;
        }

        std::vector<GLubyte> pixels((size_t)w * h * 4);
        OpenGL::render_begin();
        GL_CALL(glBindFramebuffer(GL_FRAMEBUFFER, buffer.fb));
        GL_CALL(glViewport(0, 0, w, h));
        GL_CALL(glReadPixels(0, 0, w, h, GL_RGBA, GL_UNSIGNED_BYTE, pixels.data()));
        buffer.release();
        OpenGL::render_end();

        // box filter scale x scale, rows flipped (GL starts at the bottom)
        out_w = w / scale;
        out_h = h / scale;
        std::vector<unsigned char> rgb((size_t)out_w * out_h * 3);
        const int n = scale * scale;
        for (int y = 0; y < out_h; y++)
        {
            for (int x = 0; x < out_w; x++)
            {
                int sum[3] = {0, 0, 0};
                for (int dy = 0; dy < scale; dy++)
                {
                    const GLubyte *row = &pixels[((size_t)(h - 1 - (y * scale + dy)) * w + x * scale) * 4];
                    for (int dx = 0; dx < scale; dx++)
                    {
                        sum[0] += row[dx * 4];
                        sum[1] += row[dx * 4 + 1];
                        sum[2] += row[dx * 4 + 2];
                    }
                }

                unsigned char *out = &rgb[((size_t)y * out_w + x) * 3];
                out[0] = sum[0] / n;
                out[1] = sum[1] / n;
                out[2] = sum[2] / n;
            }
        }

        // written aside and renamed, so the shell never reads half a file
        const std::string tmp = file + ".tmp";
        FILE *f = std::fopen(tmp.c_str(), "wb");
        if (!f)
        {
            return false;
        }

        std::fprintf(f, "P6 %d %d 255 ", out_w, out_h);
        const bool ok = std::fwrite(rgb.data(), 1, rgb.size(), f) == rgb.size();
        std::fclose(f);
        if (!ok || (std::rename(tmp.c_str(), file.c_str()) != 0))
        {
            std::remove(tmp.c_str());
            return false;
        }

        return true;
    }
};

DECLARE_WAYFIRE_PLUGIN(wayfire_podglad);
