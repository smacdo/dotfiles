local wezterm = require 'wezterm'
local config = {}

-- Limit scroll speed to three lines for console. Setting `alt_screen = false`
-- means tmux and vim behavior is unchanged.
--
-- Scroll is set to three lines up/down. wezterm seems to use page up / down
-- which is imo bizzare.
config.mouse_bindings = {
  {
    event = { Down = { streak = 1, button = { WheelUp = 1 } } },
    mods = 'NONE',
    action = wezterm.action.ScrollByLine(-3),
    alt_screen = false,
  },
  {
    event = { Down = { streak = 1, button = { WheelDown = 1 } } },
    mods = 'NONE',
    action = wezterm.action.ScrollByLine(3),
    alt_screen = false,
  }
}

-- My preferred font and color scheme.
config.font = wezterm.font_with_fallback {
  'JetBrainsMono Nerd Font',
  'JetBrains Mono'
}

config.color_scheme = 'Catppuccin Mocha'

-- Allow hyperlinks.
config.hyperlink_rules = wezterm.default_hyperlink_rules()

-- Hide the title bar but keep resizable borders
config.window_decorations = "RESIZE"

-- Reduce window margins
config.window_padding = {
  left = 2,
  right = 2,
  top = 0,
  bottom = 0,
}

return config
