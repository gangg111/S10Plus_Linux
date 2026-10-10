// SPDX-FileCopyrightText: 2026 Artur <ganggg111@gmail.com>
// SPDX-License-Identifier: MIT
//
// Keeps windows out of the front camera hole (Galaxy S10+, punch hole in the
// top right corner of the panel).  With the shell panels auto-hidden every app
// gets the whole screen and the buttons of its header end up under the camera
// (Firefox tab list, Calindori menu).  Android solves it with a cutout area;
// here the same thing is a reserved strip of the workarea on the edge the hole
// is nearest to after the current rotation.
//
// The strip only tops up what is already reserved on that edge: with the
// status bar shown (67 pt at the top) the hole is covered anyway and nothing
// more is taken.

#include <wayfire/core.hpp>
#include <wayfire/idle.hpp>
#include <wayfire/nonstd/wlroots-full.hpp>
#include <wayfire/output.hpp>
#include <wayfire/per-output-plugin.hpp>
#include <wayfire/plugin.hpp>
#include <wayfire/signal-definitions.hpp>
#include <wayfire/util/log.hpp>
#include <wayfire/workarea.hpp>

#include <algorithm>

class wayfire_wyciecie : public wf::per_output_plugin_instance_t
{
    // The hole in panel pixels of the native (portrait, 1440x3040) mode,
    // measured from a photo of the screen: 371..456 x 10..48 pt at scale 3,
    // plus 4 pt to spare all around.
    static constexpr int HOLE_X = 1101, HOLE_Y = 18, HOLE_W = 279, HOLE_H = 138;
    static constexpr int MARGIN = 0; // already in the box above

    wf::output_workarea_manager_t::anchored_area area{
        wf::output_workarea_manager_t::ANCHORED_EDGE_TOP, 0, nullptr};
    bool added = false;
    wf::wl_idle_call idle_update;

    // the hole in output-local logical coordinates, for the current transform
    wf::geometry_t hole() const
    {
        wlr_output *o = output->handle;
        wlr_box b{HOLE_X, HOLE_Y, HOLE_W, HOLE_H}, t;
        wlr_box_transform(&t, &b, wlr_output_transform_invert(o->transform), o->width, o->height);
        const double s = o->scale > 0 ? o->scale : 1.0;
        return {(int)(t.x / s), (int)(t.y / s), (int)((t.width + s - 1) / s), (int)((t.height + s - 1) / s)};
    }

    void update()
    {
        const auto full = output->get_relative_geometry();
        const auto h    = hole();

        // the edge the hole is nearest to, and how deep it reaches from there
        using E = wf::output_workarea_manager_t::anchored_edge;
        const int d_top    = h.y;
        const int d_bottom = full.height - (h.y + h.height);
        const int d_left   = h.x;
        const int d_right  = full.width - (h.x + h.width);
        E edge;
        int depth;
        const int m = std::min({d_top, d_bottom, d_left, d_right});
        if (m == d_top)
        {
            edge = E::ANCHORED_EDGE_TOP, depth = h.y + h.height;
        } else if (m == d_bottom)
        {
            edge = E::ANCHORED_EDGE_BOTTOM, depth = full.height - h.y;
        } else if (m == d_left)
        {
            edge = E::ANCHORED_EDGE_LEFT, depth = h.x + h.width;
        } else
        {
            edge = E::ANCHORED_EDGE_RIGHT, depth = full.width - h.x;
        }

        depth += MARGIN;

        auto wm = output->workarea.get();
        if (!added || (edge != area.edge))
        {
            if (added)
            {
                wm->remove_reserved_area(&area);
            }

            area.edge = edge;
            area.reserved_size = 0;
            wm->add_reserved_area(&area);
            added = true;
            wm->reflow_reserved_areas();
        }

        // what the other areas (the shell panel) already keep on this edge
        const auto wa = wm->get_workarea();
        int taken = 0;
        switch (edge)
        {
          case E::ANCHORED_EDGE_TOP:
            taken = wa.y - full.y;
            break;
          case E::ANCHORED_EDGE_BOTTOM:
            taken = (full.y + full.height) - (wa.y + wa.height);
            break;
          case E::ANCHORED_EDGE_LEFT:
            taken = wa.x - full.x;
            break;
          case E::ANCHORED_EDGE_RIGHT:
            taken = (full.x + full.width) - (wa.x + wa.width);
            break;
        }

        const int others = taken - area.reserved_size;
        const int want   = std::max(0, depth - others);
        if (want != area.reserved_size)
        {
            LOGI("wyciecie: edge ", (int)edge, ", hole ", h, ", panel keeps ", others, ", reserving ", want);
            area.reserved_size = want;
            wm->reflow_reserved_areas();
        }
    }

    // not from inside the signal: the workarea is being reflowed right then
    void schedule()
    {
        idle_update.run_once([=] () { update(); });
    }

    wf::signal::connection_t<wf::workarea_changed_signal> on_workarea = [=] (wf::workarea_changed_signal*)
    {
        schedule();
    };

    wf::signal::connection_t<wf::output_configuration_changed_signal> on_config =
        [=] (wf::output_configuration_changed_signal*)
    {
        schedule();
    };

  public:
    void init() override
    {
        output->connect(&on_workarea);
        output->connect(&on_config);
        update();
    }

    void fini() override
    {
        idle_update.disconnect();
        if (added)
        {
            output->workarea->remove_reserved_area(&area);
            output->workarea->reflow_reserved_areas();
        }
    }
};

DECLARE_WAYFIRE_PLUGIN(wf::per_output_plugin_t<wayfire_wyciecie>);
