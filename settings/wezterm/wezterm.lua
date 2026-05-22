local wezterm = require 'wezterm'
local config = {}

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
