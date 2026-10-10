// SPDX-FileCopyrightText: 2026 Artur <ganggg111@gmail.com>
// SPDX-License-Identifier: MIT
//
// Screen rotation from iio-sensor-proxy, in place of wayfire's autorotate-iio
// (MIT, its bindings and sensor names kept).  Two things differ:
//
// 1. autorotate-iio switched the output transform at once.  The clients still
//    had portrait buffers then (480 of the 1013 logical columns of a landscape
//    screen), so for a while about half of the screen showed old content and
//    the rest was black, until every client redrew at its new size.  Here the
//    last frame is kept (post hook) and shown unchanged on the panel until
//    every surface on the output has committed after the transform change
//    (or WAIT_MS passed), then it fades into the live image.
//
// 2. autorotate-iio iterated the GLib main loop once a second, so a turn of
//    the phone took effect up to a second late.  Here GLib runs its own
//    context in a thread and wakes the compositor through an eventfd, only
//    when the orientation really changes.

#include <wayfire/core.hpp>
#include <wayfire/input-device.hpp>
#include <wayfire/opengl.hpp>
#include <wayfire/output.hpp>
#include <wayfire/output-layout.hpp>
#include <wayfire/per-output-plugin.hpp>
#include <wayfire/plugin.hpp>
#include <wayfire/render-manager.hpp>
#include <wayfire/signal-definitions.hpp>
#include <wayfire/util.hpp>
#include <wayfire/util/log.hpp>
#include <wayfire/view.hpp>
#include <wayfire/nonstd/wlroots-full.hpp>

#include <gio/gio.h>
#include <sys/eventfd.h>
#include <unistd.h>

#include <map>
#include <memory>
#include <mutex>
#include <string>
#include <thread>

static const char *vertex_shader = R"(
#version 100
attribute mediump vec2 position;
attribute highp vec2 uvPosition;
varying highp vec2 uvpos;
void main()
{
    gl_Position = vec4(position.xy, 0.0, 1.0);
    uvpos = uvPosition;
}
)";

// premultiplied: opaque copy at alpha 1, fading frozen frame below 1
static const char *fragment_shader = R"(
#version 100
varying highp vec2 uvpos;
uniform sampler2D smp;
uniform mediump float alpha;
void main()
{
    gl_FragColor = vec4(texture2D(smp, uvpos).rgb, 1.0) * alpha;
}
)";

class wayfire_obrot : public wf::per_output_plugin_instance_t
{
    // longest wait for the clients, then the fade starts anyway
    static constexpr int64_t WAIT_MS = 1000;
    static constexpr int64_t FADE_MS = 200;

    wf::option_wrapper_t<wf::activatorbinding_t>
    rotate_up_opt{"autorotate-iio/rotate_up"},
    rotate_left_opt{"autorotate-iio/rotate_left"},
    rotate_down_opt{"autorotate-iio/rotate_down"},
    rotate_right_opt{"autorotate-iio/rotate_right"};
    wf::option_wrapper_t<bool> config_rotation_locked{"autorotate-iio/lock_rotation"};

    wf::plugin_activation_data_t grab_interface{
        .name = "obrot",
        .capabilities = 0,
    };

    int32_t user_rotation   = -1;
    int32_t sensor_transform = -1;

    // rotation sequence
    enum class stage { IDLE, CAPTURE, FROZEN, FADE };
    stage st = stage::IDLE;
    wl_output_transform target = WL_OUTPUT_TRANSFORM_NORMAL;
    wf::framebuffer_t frozen;
    OpenGL::program_t program;
    bool hooked = false;
    int64_t frozen_since = 0, fade_since = 0;
    wf::wl_idle_call idle_apply;

    // surfaces that still owe a commit after the transform change
    struct pending_surface
    {
        wf::wl_listener_wrapper on_commit;
        wf::wl_listener_wrapper on_destroy;
    };
    std::map<wlr_surface*, std::unique_ptr<pending_surface>> pending;

    // sensor thread
    std::thread glib_thread;
    GMainContext *glib_ctx = nullptr;
    GMainLoop *glib_loop   = nullptr;
    GDBusProxy *proxy = nullptr;
    guint watch_id    = 0;
    int wake_fd = -1;
    wl_event_source *wake_source = nullptr;
    std::mutex orientation_lock;
    std::string orientation;

  public:
    void init() override
    {
        output->add_activator(rotate_left_opt, &on_rotate_left);
        output->add_activator(rotate_right_opt, &on_rotate_right);
        output->add_activator(rotate_up_opt, &on_rotate_up);
        output->add_activator(rotate_down_opt, &on_rotate_down);

        on_input_devices_changed.emit(nullptr);
        wf::get_core().connect(&on_input_devices_changed);

        OpenGL::render_begin();
        program.set_simple(OpenGL::compile_program(vertex_shader, fragment_shader));
        OpenGL::render_end();

        idle_apply.set_callback([=] () { apply_target(); });
        start_sensor_thread();
    }

    void fini() override
    {
        output->rem_binding(&on_rotate_left);
        output->rem_binding(&on_rotate_right);
        output->rem_binding(&on_rotate_up);
        output->rem_binding(&on_rotate_down);
        stop_sensor_thread();
        idle_apply.disconnect();
        finish();
        OpenGL::render_begin();
        program.free_resources();
        frozen.release();
        OpenGL::render_end();
    }

  private:
    bool is_autorotate_enabled()
    {
        static const std::string integrated_connectors[] = {
            "HWCOMPOSER-1", "eDP", "LVDS", "DSI",
        };
        const std::string name = output->handle->name;
        for (const auto& c : integrated_connectors)
        {
            if (name.find(c) != std::string::npos)
            {
                return true;
            }
        }

        return false;
    }

    wf::signal::connection_t<wf::input_device_added_signal> on_input_devices_changed = [=] (void*)
    {
        if (!is_autorotate_enabled())
        {
            return;
        }

        for (auto& dev : wf::get_core().get_input_devices())
        {
            if (dev->get_wlr_handle()->type == WLR_INPUT_DEVICE_TOUCH)
            {
                wlr_cursor_map_input_to_output(wf::get_core().get_wlr_cursor(),
                    dev->get_wlr_handle(), output->handle);
            }
        }
    };

    wf::activator_callback on_rotate_left  = [=] (auto) { return on_rotate_binding(WL_OUTPUT_TRANSFORM_90); };
    wf::activator_callback on_rotate_right = [=] (auto) { return on_rotate_binding(WL_OUTPUT_TRANSFORM_270); };
    wf::activator_callback on_rotate_up    = [=] (auto) { return on_rotate_binding(WL_OUTPUT_TRANSFORM_NORMAL); };
    wf::activator_callback on_rotate_down  = [=] (auto) { return on_rotate_binding(WL_OUTPUT_TRANSFORM_180); };

    bool on_rotate_binding(int32_t target_rotation)
    {
        if (!output->can_activate_plugin(&grab_interface))
        {
            return false;
        }

        // the same binding twice unlocks the rotation again
        user_rotation = (target_rotation == user_rotation) ? -1 : target_rotation;
        return update_transform();
    }

    bool update_transform()
    {
        int32_t want;
        if (user_rotation >= 0)
        {
            want = user_rotation;
        } else if ((sensor_transform >= 0) && !config_rotation_locked)
        {
            want = sensor_transform;
        } else
        {
            return false;
        }

        if ((st == stage::IDLE) &&
            (wf::get_core().output_layout->get_current_configuration()[output->handle].transform ==
             (wl_output_transform)want))
        {
            return false;
        }

        target = (wl_output_transform)want;
        switch (st)
        {
          case stage::IDLE:
            // keep the frame on the panel first, rotate on the next idle
            st = stage::CAPTURE;
            hook_on();
            output->render->damage_whole();
            break;

          case stage::CAPTURE:
            // the capture is still coming, it will apply the newest target
            break;

          case stage::FROZEN:
            // the frozen frame is still the right picture, just turn again
            idle_apply.run_once();
            break;

          case stage::FADE:
            // the live image is partly visible: no clean frame to keep
            finish();
            return update_transform();
        }

        return true;
    }

    void apply_target()
    {
        auto config = wf::get_core().output_layout->get_current_configuration();
        if (config[output->handle].transform != target)
        {
            config[output->handle].transform = target;
            wf::get_core().output_layout->apply_configuration(config);
        }

        LOGI("obrot: transform ", (int)target, ", waiting for the clients");
        st = stage::FROZEN;
        frozen_since = wf::get_current_time();
        watch_surfaces();
        output->render->damage_whole();
    }

    // every mapped surface on this output redraws after the transform change
    void watch_surfaces()
    {
        pending.clear();
        for (auto& view : wf::get_core().get_all_views())
        {
            if (!view->is_mapped() || (view->get_output() != output))
            {
                continue;
            }

            auto surface = view->get_wlr_surface();
            if (!surface || pending.count(surface))
            {
                continue;
            }

            auto p = std::make_unique<pending_surface>();
            p->on_commit.set_callback([=] (void*) { done_surface(surface); });
            p->on_commit.connect(&surface->events.commit);
            p->on_destroy.set_callback([=] (void*) { done_surface(surface); });
            p->on_destroy.connect(&surface->events.destroy);
            pending[surface] = std::move(p);
        }
    }

    void done_surface(wlr_surface *surface)
    {
        // not erased here: this runs inside the listener being destroyed
        auto it = pending.find(surface);
        if (it != pending.end())
        {
            it->second->on_commit.disconnect();
            it->second->on_destroy.disconnect();
        }

        output->render->damage_whole();
    }

    bool clients_ready()
    {
        for (auto& [s, p] : pending)
        {
            if (p->on_commit.is_connected())
            {
                return false;
            }
        }

        return true;
    }

    void hook_on()
    {
        if (!hooked)
        {
            output->render->add_post(&hook);
            output->render->set_redraw_always(true);
            hooked = true;
        }
    }

    void finish()
    {
        if (hooked)
        {
            output->render->rem_post(&hook);
            output->render->set_redraw_always(false);
            hooked = false;
        }

        pending.clear();
        st = stage::IDLE;
        output->render->damage_whole();
    }

    wf::post_hook_t hook = [=] (const wf::framebuffer_t& source, const wf::framebuffer_t& destination)
    {
        const int64_t now = wf::get_current_time();
        switch (st)
        {
          case stage::IDLE:
            draw(source, destination, 1.0f);
            break;

          case stage::CAPTURE:
            OpenGL::render_begin();
            frozen.allocate(source.viewport_width, source.viewport_height);
            OpenGL::render_end();
            draw(source, frozen, 1.0f);
            draw(source, destination, 1.0f);
            // the transform cannot change in the middle of a frame
            idle_apply.run_once();
            break;

          case stage::FROZEN:
            draw(frozen, destination, 1.0f);
            if (clients_ready() || (now - frozen_since >= WAIT_MS))
            {
                LOGI("obrot: clients ", clients_ready() ? "ready" : "late", " after ",
                    now - frozen_since, " ms");
                st = stage::FADE;
                fade_since = now;
            }

            break;

          case stage::FADE:
          {
            const float p = std::min(1.0f, (float)(now - fade_since) / FADE_MS);
            draw(source, destination, 1.0f);
            draw(frozen, destination, 1.0f - p, true);
            if (p >= 1.0f)
            {
                // not from inside the render pass
                idle_finish.run_once([=] () { finish(); });
            }

            break;
          }
        }
    };

    wf::wl_idle_call idle_finish;

    void draw(const wf::framebuffer_t& from, const wf::framebuffer_t& to, float alpha,
        bool blend = false)
    {
        static const float vertex_data[] = {-1.0f, -1.0f, 1.0f, -1.0f, 1.0f, 1.0f, -1.0f, 1.0f};
        static const float coord_data[]  = {0.0f, 0.0f, 1.0f, 0.0f, 1.0f, 1.0f, 0.0f, 1.0f};

        OpenGL::render_begin(to);
        program.use(wf::TEXTURE_TYPE_RGBA);
        GL_CALL(glActiveTexture(GL_TEXTURE0));
        GL_CALL(glBindTexture(GL_TEXTURE_2D, from.tex));
        program.attrib_pointer("position", 2, 0, vertex_data);
        program.attrib_pointer("uvPosition", 2, 0, coord_data);
        program.uniform1f("alpha", alpha);
        if (blend)
        {
            GL_CALL(glEnable(GL_BLEND));
            GL_CALL(glBlendFunc(GL_ONE, GL_ONE_MINUS_SRC_ALPHA));
        } else
        {
            GL_CALL(glDisable(GL_BLEND));
        }

        GL_CALL(glDrawArrays(GL_TRIANGLE_FAN, 0, 4));
        GL_CALL(glEnable(GL_BLEND));
        GL_CALL(glBindTexture(GL_TEXTURE_2D, 0));
        program.deactivate();
        OpenGL::render_end();
    }

    // ---- iio-sensor-proxy, in a thread with its own GLib context ----

    void start_sensor_thread()
    {
        if (!is_autorotate_enabled())
        {
            return;
        }

        wake_fd = eventfd(0, EFD_CLOEXEC | EFD_NONBLOCK);
        if (wake_fd < 0)
        {
            LOGE("obrot: eventfd failed");
            return;
        }

        wake_source = wl_event_loop_add_fd(wf::get_core().ev_loop, wake_fd, WL_EVENT_READABLE,
            [] (int fd, uint32_t, void *data)
        {
            uint64_t n;
            while (read(fd, &n, sizeof(n)) > 0)
            {}

            ((wayfire_obrot*)data)->on_orientation();
            return 0;
        }, this);

        glib_ctx  = g_main_context_new();
        glib_loop = g_main_loop_new(glib_ctx, FALSE);
        glib_thread = std::thread([=] ()
        {
            g_main_context_push_thread_default(glib_ctx);
            watch_id = g_bus_watch_name(G_BUS_TYPE_SYSTEM, "net.hadess.SensorProxy",
                G_BUS_NAME_WATCHER_FLAGS_NONE, on_name_appeared, on_name_vanished, this, nullptr);
            g_main_loop_run(glib_loop);
            if (watch_id)
            {
                g_bus_unwatch_name(watch_id);
            }

            if (proxy)
            {
                g_object_unref(proxy);
                proxy = nullptr;
            }

            // let the unwatch and unref finish their pending work
            while (g_main_context_iteration(glib_ctx, FALSE))
            {}

            g_main_context_pop_thread_default(glib_ctx);
        });
    }

    void stop_sensor_thread()
    {
        if (glib_loop)
        {
            g_main_loop_quit(glib_loop);
            glib_thread.join();
            g_main_loop_unref(glib_loop);
            g_main_context_unref(glib_ctx);
            glib_loop = nullptr;
            glib_ctx  = nullptr;
        }

        if (wake_source)
        {
            wl_event_source_remove(wake_source);
            wake_source = nullptr;
        }

        if (wake_fd >= 0)
        {
            close(wake_fd);
            wake_fd = -1;
        }
    }

    // GLib thread
    static void on_name_appeared(GDBusConnection *conn, const gchar *name,
        const gchar*, gpointer data)
    {
        auto self = (wayfire_obrot*)data;
        GError *err = nullptr;
        self->proxy = g_dbus_proxy_new_sync(conn, G_DBUS_PROXY_FLAGS_NONE, nullptr, name,
            "/net/hadess/SensorProxy", "net.hadess.SensorProxy", nullptr, &err);
        if (!self->proxy)
        {
            LOGE("obrot: no iio-sensor-proxy: ", err ? err->message : "?");
            g_clear_error(&err);
            return;
        }

        g_signal_connect(self->proxy, "g-properties-changed", G_CALLBACK(on_properties_changed), self);
        GVariant *r = g_dbus_proxy_call_sync(self->proxy, "ClaimAccelerometer", nullptr,
            G_DBUS_CALL_FLAGS_NONE, -1, nullptr, &err);
        if (r)
        {
            g_variant_unref(r);
        } else
        {
            LOGE("obrot: ClaimAccelerometer: ", err ? err->message : "?");
            g_clear_error(&err);
        }

        LOGI("obrot: iio-sensor-proxy connected");
        self->post_orientation();
    }

    static void on_name_vanished(GDBusConnection*, const gchar*, gpointer data)
    {
        auto self = (wayfire_obrot*)data;
        if (self->proxy)
        {
            g_object_unref(self->proxy);
            self->proxy = nullptr;
        }
    }

    static void on_properties_changed(GDBusProxy*, GVariant*, const gchar *const*, gpointer data)
    {
        ((wayfire_obrot*)data)->post_orientation();
    }

    void post_orientation()
    {
        GVariant *v = g_dbus_proxy_get_cached_property(proxy, "AccelerometerOrientation");
        if (!v)
        {
            return;
        }

        {
            std::lock_guard<std::mutex> g(orientation_lock);
            orientation = g_variant_get_string(v, nullptr);
        }

        g_variant_unref(v);
        uint64_t one = 1;
        if (write(wake_fd, &one, sizeof(one)) < 0)
        {}
    }

    // compositor thread
    void on_orientation()
    {
        std::string o;
        {
            std::lock_guard<std::mutex> g(orientation_lock);
            o = orientation;
        }

        static const std::map<std::string, wl_output_transform> transform_by_name = {
            {"normal", WL_OUTPUT_TRANSFORM_NORMAL},
            {"left-up", WL_OUTPUT_TRANSFORM_90},
            {"right-up", WL_OUTPUT_TRANSFORM_270},
            {"bottom-up", WL_OUTPUT_TRANSFORM_180},
        };
        auto it = transform_by_name.find(o);
        if (it == transform_by_name.end())
        {
            return;
        }

        LOGI("obrot: accelerometer ", o);
        sensor_transform = it->second;
        update_transform();
    }
};

DECLARE_WAYFIRE_PLUGIN(wf::per_output_plugin_t<wayfire_obrot>);
