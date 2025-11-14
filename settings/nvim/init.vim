" Scott's vimrc
"===============================================================================
" # Notes
" Leader is ,
"
" ## Custom shortcuts:
"  ANY MODE
"   F2           Toggle no indent when pasting mode.
"   CTRL M       Reset highlighted text.
"   CTRL hjkl    Switch between split panes.
"   <leader> sv  Source .vimrc in current session.
"   <leader> ev  Edit .vimrc in new split.
"
"  INSERT MODE
"   CTRL v       Paste from system clipboard.
"
"  VISUAL MODE
"   CTRL C       Copy selection to system clipboard.
"   CTRL D       Cut selection to system clipboard.
"
" ## Useful shortcuts to remember:
"  %    - Jump between pairs of characters like {} () [] if/else

"===============================================================================
"  General settings.
"===============================================================================
" Command leader.
let mapleader = ","
let maplocalleader = "\\"

" Language independent tab settings which can be overriden when *vi loads a file
" with custom rules.
set tabstop=2     " Insert 2 space characters rather than a hard tab (\t).
set shiftwidth=2  " Insert 2 spaces when auto indenting or hitting << >> or == .
set softtabstop=2 " Treat 2 spaces as a tab when hitting tab, deleting, etc.
set expandtab     " Insert `$softtabstop` # spaces when tab is pushed.
set shiftround    " Round indentation to multiple of shift width.
set autoindent    " Copy indentation from previous line when starting new line.

" Set the (default) maximum column to 100, which is sometimes overriden by a
" file types with custom rules.
set textwidth=100

" Show a ruler at column 80, and then a wider ruler at 100-105.
if exists('&colorcolumn')
  set colorcolumn=80,100,101,102,103,104,105
endif

" Keep NNN lines of command history which persists through editor sessions.
set history=10000

" Show line numbers on the left side of the editor.
set number

" Show the matching brace under the curosr.
set showmatch

" Show the partial command in the command bar. Useful when highlighting text
" in visual mode, as it will show the number of chars / lines highlighted.
set showcmd

" Use case insensitive matching, but only if all of the characters are
" lowercase.
set ignorecase      " Ignore case when matching...
set smartcase       " ...unless a character is upper case.

" Searching configuration.
set incsearch  " Use incremental searching. Hit `<CR>` to stop.
set hlsearch   " Highlight all search patterns.

" Always draw a status line even if there is one window.
set laststatus=2

" Keep two lines above or below the cursor when scrolling vertically.
set scrolloff=1

" Keep five characters to the left / right when scrolling horizontally.
set sidescrolloff=5

" The system bell is never not annoying. Just don't.
set noerrorbells

" Enable automatic backups.
set backup

" Use a dialog to confirm changes when saving instead of erroring out.
set confirm

" Automatically save buffer before commands like :next, :make, etc.
set autowrite

" Shows the active mode on the status line (ie --INSERT--), which is helpful
" if the airline plugin is not loaded.
set showmode

" Allow more than one unsaved buffer.
set hidden

" Use bash-like tab completion when in command prompt.
set wildmode=list:longest,full

" Make backspace work as expected on some oddly configured platforms. 
set backspace=eol,start,indent

" Use case insensitive file name completion.
if exists('&wildignorecase')
  set wildignorecase
endif

" Make error messages be red on white.
highlight ErrorMsg guibg=White guifg=Red

"===============================================================================
" Custom shortcuts.
"===============================================================================
" Open and source .vimrc file.
:noremap <leader>ev :vsplit $MYVIMRC<cr>     " Open .vimrc in a split.
:noremap <leader>sv :source $MYVIMRC<cr>     " Source .vimrc.

" Use CTRL+hjkl to move between window panes (splits).
noremap <silent> <C-k> :wincmd k<CR>
noremap <silent> <C-j> :wincmd j<CR>
noremap <silent> <C-h> :wincmd h<CR>
noremap <silent> <C-l> :wincmd l<CR>

" Map <F2> to a toggle switch that enables or disables vim's auto indent on
" paste. Use this when you want to paste code without applying indent rules.
if !has('nvim')
  noremap <F2> :set invpaste paste?<CR>
  set pastetoggle=<F2>
endif

" Use <C-M> to clear highlighting from :set hlsearch.
if maparg('<C-M>', 'n') ==# ''
  noremap <silent> <C-M> :nohlsearch<C-R>=has('diff')?'<Bar>diffupdate':''<CR><CR><C-L>
endif

" Copy/cut/paste from system clipboard.
:inoremap <C-v> <ESC>"+pa
:vnoremap <C-c> "+y
:vnoremap <C-d> "+d

"===============================================================================
" Plugins
"===============================================================================
" Note to readers: Make sure to call :PlugInstall after updating the plugin
" list.
call plug#begin(has('nvim') ? stdpath('data') . '/plugged' : '~/.vim/plugged')

" Language server protocol.
if has('nvim')
    Plug 'neovim/nvim-lspconfig'
endif

" Color scheme: Use a custom theme for neovim, and Solarized for vim. Helps to
" distinguish when neovim is not installed on a machine.
if has('nvim')
  Plug 'catppuccin/nvim', { 'as': 'catppuccin' }
else

endif

" Pretty status bar.
Plug 'vim-airline/vim-airline'
Plug 'vim-airline/vim-airline-themes'

" Show buffers in the command bar.
Plug 'bling/vim-bufferline'

" Git integration.
Plug 'tpope/vim-fugitive'

" List ends here. Plugins become visible to Vim after this call.
call plug#end()

"===============================================================================
" Colorscheme
"===============================================================================
set termguicolors

if has('nvim')
  " Neovim uses a custom theme to distinguish visually from vim.
  colorscheme catppuccin " catppuccin-latte, catppuccin-frappe, catppuccin-macchiato, catppuccin-mocha
else
  " Vim uses my older theme Solarized as a way to distinguish from neovim.
  set background=dark
  colorscheme solarized8
endif

"===============================================================================
"  Status line
"===============================================================================
" Display line and column position in the status line.
set ruler

" Custom settings for airline theme.
if &runtimepath =~ 'vim-airline'
  let g:airline_theme = 'dark'

  " Display all buffers when one tab is open.
  let g:airline#extensions#tabline#enabled = 1

  " Use fancy font glyphs for the status line. Requires a terminal font that
  " supports powerline.
  let g:airline_powerline_fonts = 1
endif

"===============================================================================
" Custom behaviors.
"===============================================================================
" Automatically switch to the directory that the document is in.
autocmd BufEnter * execute "chdir ".escape(expand("%:p:h"), ' ')

" Jump from if to corresponding else when using %.
runtime macros/matchit.vim

" Open file to the last edited position.
if has("autocmd")
  au BufReadPost * if line("'\'") > 0 && line("'\"") <= line("$")
    \| exe "normal g'\"" | endif
endif

" Turn on automatic syntax highlighting, indenting and other features for files
" that have a detected language.
if has('autocmd')
  filetype plugin indent on
endif

if has('syntax') && !exists('g:syntax_on')
  syntax enable
endif

" Set the amount of time for vim to wait when checking for a multi-key command
" to 100ms.
if !has('nvim') && &ttimeoutlen == -1
  set ttimeout
  set ttimeoutlen=100
endif

" Enable mouse support by default since all modern terminals have support for
" mice.
if has('mouse')
  set mouse=a
endif

" Set a single well known location for vim to store user state (backup, temp,
" etc) and if those directories don't exist create them.
" TODO: Create a crontab script to nuke files after ~ 90 days.
if !isdirectory($HOME."/.local/state/vim/backups")
  call mkdir($HOME."/.local/state/vim/backups", "p", 0770)
endif

if !isdirectory($HOME."/.local/state/vim/tmp")
  call mkdir($HOME."/.local/state/vim/tmp", "p", 0770)
endif

if !isdirectory($HOME."/.local/state/vim/undo")
  call mkdir($HOME."/.local/state/vim/undo", "p", 0770)
endif

set backupdir=$HOME/.local/state/vim/backups  " File back up in case of crash.
set directory=$HOME/.local/state/vim/tmp      " Stores temporary file state.
set undodir=$HOME/.local/state/vim/undo       " Stores undo history for files.

"===============================================================================
" Custom file type detectors.
"===============================================================================
" Buck build files use the Starlark language but lack file extension detection.
au BufRead,BufNewFile * if expand('%:t') == 'BUCK' | set filetype=bzl | endif
au BufRead,BufNewFile * if expand('%:t') =~# '^TARGETS\(\.v[12]\)\?$' | set filetype=bzl | endif

"===============================================================================
" Machine local settings.
"===============================================================================
let $MY_LOCAL_VIMRC = $HOME . "/.my_vimrc"

if filereadable($MY_LOCAL_VIMRC)
  source $MY_LOCAL_VIMRC
endif