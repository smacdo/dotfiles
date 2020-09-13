"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
" Scott's .vimrc                                                          "
" ----------------------------------------------------------------------- "
" Custom Command List                                                     "
" --------------------                                                    "
"                                                                         "
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
" This line should not be removed as it ensures that various options are
" properly set to work with the Vim-related packages available in Debian.
" TODO: Only source this on debian, source correct platform specific.
runtime! debian.vim

" Use Vim settings rather than vi settings. Avoid side effects if compatible
" is already reset.
if &compatible
    set nocompatible
endif

" My default editor theme is molkai.
colorscheme molokai

" Basic editor settings.
set history=1000  " Keep 100 lines of command history. You know, just in case.
set expandtab     " Insert $softtabstop amount of spaces when tab is pushed instead of \t.
set tabstop=4     " Change width of hard tab to 4 spaces.
set shiftwidth=4  " Use 4 spaces when auto indenting, hitting >> << or ==.
set softtabstop=4 " Treat 4 spaces as a tab when hitting tab, deleting etc. 
set shiftround    " Round indent to multiple of shiftwidth ('>', '<').
set autoindent    " Copies indentation from previous line when starting a new line.
set textwidth=120 " Maximum width of text that is being inserted before being broken up.
set number        " Display line numbers in left column.
set showmode      " Shows mode at bottom (ie --INSERT--).
set wildmode=list:longest,full " Bash-like tab completion when in conmmand prompt.
set ruler         " Show line/col pos in status line
set showmatch     " Always show matching brace under cursor
set noerrorbells  " System bell is pure evil
set background=dark " Set dark background for colors
set bg=dark       " Set dark background for colors
set autoread      " Set readonly when file is external modified.
set showcmd       " Show (partial) command in status line.
set ignorecase    " Case insensitive matching.
set smartcase     " Overrides ignorecase when at least one non-lowercase character is present.
set incsearch     " Incremental search. Hit `<CR>` to stop.
set autowrite     " Automatically save before commands like :next, :make etc.
set hidden        " Possibility to have more than one unsaved buffer.
set hlsearch      " Highlight all search pattern mathes.
set laststatus=2  " Always draw a status line even if there is only one window.
set scrolloff=1   " Keep two lines above/below cursor when scrolling up/down.
set sidescrolloff=5 " Keep five characters to left/right when scrolling horizontally.
set backup        " Enable automatic backups.
set backupdir=~/.vim_runtime/backups " Store backups in a central location.
set directory=~/.vim_runtime/tmp     " Keep .swp files in one out of the way directory.

" Automatically switches to the directory that the document is in
autocmd BufEnter * execute "chdir ".escape(expand("%:p:h"), ' ')

" Make backspace act as expected on some weirdly configured platforms
set backspace=eol,start,indent

" Map <F2> to enable/disable vim's auto ident on paste. This allows us to paste code without
" having the auto indentation rules applied.
nnoremap <F2> :set invpaste paste?<CR>
set pastetoggle=<F2>

" Hit % on a 'if' to jump to the corresponding else.
runtime macros/matchit.vim

"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
" Enhanced status line                                                    "
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
" Recalculate the trailing whitespace warning when idle, and after saving
autocmd cursorhold,bufwritepost * unlet! b:statusline_trailing_space_warning

" Recalculate the tab warning flag when idle and after writing
autocmd cursorhold,bufwritepost * unlet! b:statusline_tab_warning

" Recalculate the long line warning when idle and after saving
autocmd cursorhold,bufwritepost * unlet! b:statusline_long_line_warning

"statusline setup
set statusline=%f "tail of the filename

"display a warning if file format isnt unix
set statusline+=%#warningmsg#
set statusline+=%{&ff!='unix'?'['.&ff.']':''}
set statusline+=%*

"display a warning if file encoding isnt utf-8
set statusline+=%#warningmsg#
set statusline+=%{(&fenc!='utf-8'&&&fenc!='')?'['.&fenc.']':''}
set statusline+=%*

set statusline+=%h "help file flag
set statusline+=%y "filetype
set statusline+=%r "read only flag
set statusline+=%m "modified flag

"display a warning if &et is wrong, or we have mixed-indenting
set statusline+=%#error#
set statusline+=%{StatuslineTabWarning()}
set statusline+=%*

set statusline+=%{StatuslineTrailingSpaceWarning()}
set statusline+=%{StatuslineLongLineWarning()}

set statusline+=%#warningmsg#
set statusline+=%{SyntasticStatuslineFlag()}
set statusline+=%*

"display a warning if &paste is set
set statusline+=%#error#
set statusline+=%{&paste?'[paste]':''}
set statusline+=%*

set statusline+=%= "left/right separator

function! SlSpace()
    if exists("*GetSpaceMovement")
        return "[" . GetSpaceMovement() . "]"
    else
        return ""
    endif
endfunc
set statusline+=%{SlSpace()}

set statusline+=%{StatuslineCurrentHighlight()}\ \ "current highlight
set statusline+=%c, "cursor column
set statusline+=%l/%L "cursor line/total lines
set statusline+=\ %P "percent through file

" have error messages red on white
highlight ErrorMsg guibg=White guifg=Red

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
"              | +-- modified flag in square brackets
"              +-- full path to file in the buffer

" Uncomment the following to have Vim jump to the last position when
" reopening a file
if has("autocmd")
  au BufReadPost * if line("'\"") > 0 && line("'\"") <= line("$")
    \| exe "normal g'\"" | endif
endif

" Persistent undo
try
    if MySys() == "windows"
        set undodir=C:\Windows\Temp
    else
        set undodir=~/.vim_runtime/undo
    endif

    set undofile
catch
endtry

" Set guide bar at 100 characters.
if exists('&colorcolumn')
    set colorcolumn=100
    highlight ColorColumn ctermbg=0 guibg=lightgrey
endif

" Case insensitive file name completion.
if exists('&wildignorecase')
    set wildignorecase
endif

" Enable file detection and turn on automatic syntax highlighting, indenting and other features
" for files with a detected language.
if has('autocmd')
    filetype plugin indent on
endif

if has('syntax') && !exists('g:syntax_on')
    syntax enable
endif

" Highlight strings and numbers inside of C comments.
let c_comment_strings=1

" Set the amount of time for vim to wait to see if a key is part of a multi-key command to
" 100ms.
if !has('nvim') && &ttimeoutlen == -1
    set ttimeout
    set ttimeoutlen=100
endif

" Use <C-L> to clear the highlighting from :set hlsearch.
if maparg('<C-L>', 'n') ==# ''
    noremap <silent> <C-L> :nohlsearch<C-R>=has('diff')?'<Bar>diffupdate':''<CR><CR><C-L>
endif

" Don't use Ex mode. Instead use Q for formatting. Revert this wtith ":unma Q"
map Q qq

" Most modern terminal support the mouse, so lets turn it on. Only xterm can grab the mouse
" event using the shift key; for other terminals use ":", select the text and press Esc.
if has('mouse')
    if &term =~ 'xterm'
        set mouse=a
    else
        set mouse=nvi
    endif
endif

" Shader file types
au BufNewFile,BufRead *.frag,*.vert,*.fp,*.vp,*.glsl,*.vs,*.fs,*.shader setf glsl

" Match doxygen todo
match Todo /@todo/

" Set shell according to platform.
" TODO: Don't do this.
if has("mac")
    set shell=/bin/zsh
elseif has("linux")
    set shell=/bin/bash
endif

" Apply GUI specific settings.
if has("gui_running")
    " Get rid of the tearoff menu entries in Windows.
    if has('win32')
        set guioption-=t
    endif

    " Show more lines and columns in GUI mode. Assumes GUI running with decent resolution.
    set lines=36
    set columns=125

    " Set a nice font. Note that Consolas isn't available by default on Linux,
    " but you can easily extract it from Microsoft's PPT installer. Its a nice
    " font made specifically for programmers!
    if has("mac")
        set guifont=Monaco:h10
    elseif has("unix")
        " TODO: Can we detect which fonts are installed in order of preference?
        set guifont=Consolas\ 12
        "set guifont=Ubuntu\ Mono\ 11
        "set guifont=Liberation\ Mono\ 10
    elseif has("win32")
        set guifont=Consolas\ 10
    endif
else
    " Settings specific to non-GUI instances.
endif

" Remap apple keys, useful because i always hit apple instead of ctrl
if has("mac")
    cmap <D-f> <C-f>
    cmap <D-b> <C-b>
endif

"return '[\s]' if trailing white space is detected
"return '' otherwise
function! StatuslineTrailingSpaceWarning()
    if !exists("b:statusline_trailing_space_warning")

        if !&modifiable
            let b:statusline_trailing_space_warning = ''
            return b:statusline_trailing_space_warning
        endif

        if search('\s\+$', 'nw') != 0
            let b:statusline_trailing_space_warning = '[\s]'
        else
            let b:statusline_trailing_space_warning = ''
        endif
    endif
    return b:statusline_trailing_space_warning
endfunction

"return the syntax highlight group under the cursor ''
function! StatuslineCurrentHighlight()
    let name = synIDattr(synID(line('.'),col('.'),1),'name')
    if name == ''
        return ''
    else
        return '[' . name . ']'
    endif
endfunction

"return '[&et]' if &et is set wrong
"return '[mixed-indenting]' if spaces and tabs are used to indent
"return an empty string if everything is fine
function! StatuslineTabWarning()
    if !exists("b:statusline_tab_warning")
        let b:statusline_tab_warning = ''

        if !&modifiable
            return b:statusline_tab_warning
        endif

        let tabs = search('^\t', 'nw') != 0

        "find spaces that arent used as alignment in the first indent column
        let spaces = search('^ \{' . &ts . ',}[^\t]', 'nw') != 0

        if tabs && spaces
            let b:statusline_tab_warning = '[mixed-indenting]'
        elseif (spaces && !&et) || (tabs && &et)
            let b:statusline_tab_warning = '[&et]'
        endif
    endif
    return b:statusline_tab_warning
endfunction

"return a warning for "long lines" where "long" is either &textwidth or 80 (if
"no &textwidth is set)
"
"return '' if no long lines
"return '[#x,my,$z] if long lines are found, were x is the number of long
"lines, y is the median length of the long lines and z is the length of the
"longest line
function! StatuslineLongLineWarning()
    if !exists("b:statusline_long_line_warning")

        if !&modifiable
            let b:statusline_long_line_warning = ''
            return b:statusline_long_line_warning
        endif

        let long_line_lens = s:LongLines()

        if len(long_line_lens) > 0
            let b:statusline_long_line_warning = "[" .
                        \ '#' . len(long_line_lens) . "," .
                        \ 'm' . s:Median(long_line_lens) . "," .
                        \ '$' . max(long_line_lens) . "]"
        else
            let b:statusline_long_line_warning = ""
        endif
    endif
    return b:statusline_long_line_warning
endfunction

"return a list containing the lengths of the long lines in this buffer
function! s:LongLines()
    let threshold = (&tw ? &tw : 80)
    let spaces = repeat(" ", &ts)

    let long_line_lens = []

    let i = 1
    while i <= line("$")
        let len = strlen(substitute(getline(i), '\t', spaces, 'g'))
        if len > threshold
            call add(long_line_lens, len)
        endif
        let i += 1
    endwhile

    return long_line_lens
endfunction

"find the median of the given array of numbers
function! s:Median(nums)
    let nums = sort(a:nums)
    let l = len(nums)

    if l % 2 == 1
        let i = (l-1) / 2
        return nums[i]
    else
        return (nums[l/2] + nums[(l/2)-1]) / 2
    endif
endfunction

