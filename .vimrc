" Scott's custom .vimrc file
" ---------------------------------------------------------------------
" Custom Command List
" --------------------
"
"
" ---------------------------------------------------------------------
" This line should not be removed as it ensures that various options are
" properly set to work with the Vim-related packages available in Debian.
runtime! debian.vim

" Use UTF-8 encoding by default
"  (turn this off if we get weird file saving)
set enc=utf-8
set fenc=utf-8
set termencoding=utf-8

"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
" File type specific settings
"  (eg special settings for java files vs makefiles)
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
autocmd FileType c,cpp,h,hpp,slang set cindent
autocmd FileType java set formatoptions=croql cindent nowrap nofoldenable
autocmd FileType c    set formatoptions+=ro smartindent
autocmd FileType perl set smartindent
autocmd FileType css  set smartindent
autocmd FileType html set formatoptions+=tl
autocmd FileType html,css set noexpandtab tabstop=4
autocmd FileType make set noexpandtab shiftwidth=4

" Python autoindent
autocmd BufRead *.py set smartindent cinwords=if,elif,else,for,while,try,except,finally,def,class

" Special file types not normally detected set here
autocmd! BufRead,BufNewFile *.ics setfiletype icalendar

" Shaders
au BufNewFile,BufRead *.frag,*.vert,*.fp,*.vp,*.glsl,*.vs,*.fs,*.shader setf glsl

" SCons
au BufNewFile,BufRead SCons* setf python

" In text and LaTeX files, always limit the width of text to 76
" characters.  Also perform logical wrapping/indenting.
autocmd BufRead *.txt set tw=76 formatoptions=tcroqn2l
autocmd BufRead *.tex set tw=76

" Don't expand tabs to spaces in Makefiles
au BufEnter [Mm]akefile* set noet
au BufLeave [Mm]akefile* set et

" YAML
augroup yamlfiles
  autocmd filetype yaml setlocal   autoindent
  autocmd filetype yaml setlocal   expandtab
  autocmd filetype yaml setlocal noignorecase
  autocmd filetype yaml setlocal   shiftround
  autocmd filetype yaml setlocal   shiftwidth=4
  autocmd filetype yaml setlocal   smartindent
  autocmd filetype yaml setlocal   softtabstop=4
  autocmd filetype yaml setlocal   tabstop=4
  autocmd filetype yaml setlocal   textwidth=0
augroup END

"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
" Misc custom settings
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
" We don't need vi compat, since it only emulates old _bugs_
set nocompatible

" History mode
set history=1024
set wildmode=list:longest,full

" Use [RO] instead of [readonly]
set shortmess+=r

" Disable line wrapping
set nowrap

" Indenting: automatically indent, and use soft tabs of width 4
set autoindent
set tabstop=4 shiftwidth=4
set shiftround
set expandtab

" Enable line/col position info in status line
set ruler

" Add line numbers
set number

" Make vim place back up files in ~/.vim_backup rather than cluttering
set backup
set backupdir=~/.vim_backup

" Show matching braces always
set showmatch

" Assume terminal is of size 80, in case we're editing via SSH
set textwidth=120

" System bell is pure evil
set noerrorbells

" Reload vimrc whenever it is edited
autocmd! bufwritepost vimrc source ~/.vim/vimrc

" have error messages red on white
highlight ErrorMsg guibg=White guifg=Red

" Uncomment the following lines to turn off backups (since its already in VCS)
" set nobackup
" set nowb
" set noswapfile

" Give a list of basic file types to ignore
set wildignore=*.dll,*.o,*.obj,*.exe,*.pyc,*.jpg,*.gif,*.png,*.tga,.svn,CVS

" Sexy statusline
set statusline=%F%m%r%h%w[%L][%{&ff}]%y[%p%%][%04l,%04v]
"              | | | | |  |   |      |  |     |    |
"              | | | | |  |   |      |  |     |    + current 
"              | | | | |  |   |      |  |     |       column
"              | | | | |  |   |      |  |     +-- current line
"              | | | | |  |   |      |  +-- current % into file
"              | | | | |  |   |      +-- current syntax in 
"              | | | | |  |   |          square brackets
"              | | | | |  |   +-- current fileformat
"              | | | | |  +-- number of lines
"              | | | | +-- preview flag in square brackets
"              | | | +-- help flag in square brackets
"              | | +-- readonly flag in square brackets
"              | +-- rodified flag in square brackets
"              +-- full path to file in the buffer

" Vim5 and later versions support syntax highlighting. Uncommenting the next
" line enables syntax highlighting by default.
set t_Co=256

filetype on
filetype plugin on
syntax on

" If using a dark background within the editing area and syntax highlighting
" turn on this option as well
set background=dark
set bg=dark

" Uncomment the following to have Vim jump to the last position when
" reopening a file
if has("autocmd")
  au BufReadPost * if line("'\"") > 0 && line("'\"") <= line("$")
    \| exe "normal g'\"" | endif
endif

" Uncomment the following to have Vim load indentation rules according to the
" detected filetype. Per default Debian Vim only load filetype specific
" plugins.
if has("autocmd")
  filetype indent on
endif

" The following are commented out as they cause vim to behave a lot
" differently from regular Vi. They are highly recommended though.
set showcmd		    " Show (partial) command in status line.
set showmatch		" Show matching brackets.
set ignorecase		" Do case insensitive matching
set smartcase		" Do smart case matching
set incsearch		" Incremental search
set autowrite		" Automatically save before commands like :next and :make
set hidden          " Hide buffers when they are abandoned
set smartindent

map <C-Tab> :tabnext<CR>

" allow <BkSpc> to delete line breaks, start of insertion, and indents 
set backspace=indent,eol,start      " This fixes it

"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
" Keybindings
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
" in normal mode, F2 saves the file
map <F2> :w<CR>

" in insert mode, F2 exits insert, saves and returns to insert mode
map <F2> <ESC>:w<CR>i

" switch between header/source with F4
map <F4> :e %:p:s,.h$,.X123X,:s,.cpp$,.h,:s,.X123X$,.cpp,<CR>

"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
" Platform specific settings, depending on if we have the GUI running
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
if has("gui_running")
    " Automatically chdir into the file's directory
    set autochdir
    set mouse=a		    " Enable mouse usage (all modes) in terminals
    set columns=80      " No more, no less
    colorscheme molokai

    " Set a nice font. Note that Consolas isn't available by default on Linux,
    " but you can easily extract it from Microsoft's PPT installer. Its a nice
    " font made specifically for programmers!
    if has("mac")
        set guifont=Monaco:h10
    elseif has("unix")
"        set guifont=Consolas\ 10
        set guifont=Monospace\ 10
    elseif has("win32")
        set guifont=Consolas\ 10
    endif
else
    colorscheme molokai
endif

" Remap apple keys, useful because i always hit apple instead of ctrl
if has("mac")
    cmap <D-f> <C-f>
    cmap <D-b> <C-b>
endif
