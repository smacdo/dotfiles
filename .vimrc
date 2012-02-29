"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
" Scott's .vimrc                                                          "
" --------------                                                          "
"   Maintainer: Scott MacDonald <scott@whitespaceconsideredharmful.com>   "
"   Version: 2.0                                                          "
"                                                                         "
" ----------------------------------------------------------------------- "
" Custom Command List                                                     "
" --------------------                                                    "
"                                                                         "
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
" This line should not be removed as it ensures that various options are
" properly set to work with the Vim-related packages available in Debian.
runtime! debian.vim
set nocompatible

"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
" Basic editor settings                                               "
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
" By default, enable soft tabs which cause \t to expand to four characters
set tabstop=4 shiftwidth=4
set shiftround
set expandtab
set autoindent
set smartindent

" Automatically switches to the directory that the document is in
autocmd BufEnter * execute "chdir ".escape(expand("%:p:h"), ' ')
"set autochdir          " has some CLI weirdness

" Make backspace act as expected on some weirdly configured platforms
set backspace=eol,start,indent

" Enables/disables vim's autopaste ability, which allows us to paste code
" without having obnoxious indenting applied to it
nnoremap <F2> :set invpaste paste?<CR>
set pastetoggle=<F2>
set showmode

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

"display a warning if fileformat isnt unix
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
set laststatus=2

"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
" User interface settings                                                 "
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
set history=1024                    " History shows 1024 entries
set wildmode=list:longest,full
set shortmess+=r                    " Use [RO] instead of [readonly]
set nowrap                          " Disable auto line wrapping
set ruler                           " Show line/col pos in status line
set number                          " Display line numbers in left col
set showmatch                       " Always show matching brace under cursor
set noerrorbells                    " System bell is pure evil
set background=dark                 " Set dark background for colors
set bg=dark                         " Set dark background for colors
set autoread                        " Set readonly when file is external mod


" The following are commented out as they cause vim to behave a lot
" differently from regular Vi. They are highly recommended though.
set showcmd		    " Show (partial) command in status line.
set ignorecase		" Do case insensitive matching
set smartcase		" Do smart case matching
set incsearch		" Incremental search
set autowrite		" Automatically save before commands like :next and :make
set hidden          " Hide buffers when they are abandoned

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
"              | +-- rodified flag in square brackets
"              +-- full path to file in the buffer

" Uncomment the following to have Vim jump to the last position when
" reopening a file
if has("autocmd")
  au BufReadPost * if line("'\"") > 0 && line("'\"") <= line("$")
    \| exe "normal g'\"" | endif
endif

""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
" File back up settings                                                    "
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
" Make vim place back up files in ~/.vim_backup rather than cluttering
set backup
set backupdir=~/.vim_runtime/backups

" Uncomment the following lines to if you want to turn off back up support
" set nobackup
" set nowb
" set noswapfile

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

"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
" Misc settings                                                           "
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
" Reload vimrc whenever it is edited
autocmd! bufwritepost vimrc source ~/.vim/vimrc

" Directory for .swp files
set directory=~/.vim_runtime/tmp

" If using a dark background within the editing area and syntax highlighting
" turn on this option as well
set background=dark
set bg=dark

"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
" Custom command mappings                                                 "
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
map <C-Tab> :tabnext<CR>


"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
" File-type specific rules and settings                                   "
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
" Vim5 and later versions support syntax highlighting. Uncommenting the next
" line enables syntax highlighting by default.
filetype on
filetype plugin on
syntax on

" Instructs vim to load indentation rules according to the detected file type
if has("autocmd")
  filetype indent on
endif

" Special settings for specific file types
autocmd FileType c,cpp,h,hpp,slang set cindent
autocmd FileType java set formatoptions=croql cindent nowrap nofoldenable
autocmd FileType c    set formatoptions+=ro
autocmd FileType perl set smartindent
autocmd FileType css  set smartindent
autocmd FileType html set formatoptions+=tl
autocmd FileType html,css set noexpandtab tabstop=4
autocmd FileType make set noexpandtab shiftwidth=4

" iCalendar file type
autocmd! BufRead,BufNewFile *.ics setfiletype icalendar

" Shader file types
au BufNewFile,BufRead *.frag,*.vert,*.fp,*.vp,*.glsl,*.vs,*.fs,*.shader setf glsl

" Match doxygen todo
match Todo /@todo/

" In text and LaTeX files, always limit the width of text to 76
" characters.  Also perform logical wrapping/indenting.
autocmd BufRead *.txt set tw=76 formatoptions=tcroqn2l
autocmd BufRead *.tex set tw=76

" Don't expand tabs to spaces in Makefiles
au BufEnter [Mm]akefile* set noet
au BufLeave [Mm]akefile* set et

"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
" Python specific options                                                 "
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
au FileType python set nocident
au FileType python syn keyword pythonDecorator True None False self

"Delete trailing white space, useful for Python ;)
func! DeleteTrailingWS()
  exe "normal mz"
  %s/\s\+$//ge
  exe "normal `z"
endfunc
autocmd BufWrite *.py :call DeleteTrailingWS()

"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
" Platform specific settings, depending on if we have the GUI running
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
if has("mac")
    set shell=/bin/bash
elseif has("linux")
    set shell=/bin/bash
endif

if has("gui_running")
    " Automatically chdir into the file's directory
    set mouse=a		    " Enable mouse usage (all modes) in terminals
    set lines=36        " A healthy amount, requires a decent gui resolution
    set columns=88      " Account for column padding
    set textwidth=80    " No more, or less
    colorscheme molokai

    " Set a nice font. Note that Consolas isn't available by default on Linux,
    " but you can easily extract it from Microsoft's PPT installer. Its a nice
    " font made specifically for programmers!
    if has("mac")
        set guifont=Monaco:h10
    elseif has("unix")
        set guifont=Consolas\ 12
        "set guifont=Ubuntu\ Mono\ 11
        "set guifont=Liberation\ Mono\ 10
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

