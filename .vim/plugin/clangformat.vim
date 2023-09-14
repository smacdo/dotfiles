" Simple clang format function taken from a Stack Overflow answer.
" Ref: https://vi.stackexchange.com/a/22985
"
" This function when called will search for a '.clang-format' file in the
" current directory or a parent directory. If it finds one then it will save the
" cursor position, replace the buffer with clang format results and finally
" restore the cursor position.
function ClangFormatBuffer(verbosity)
    if !executable('clang-format')
        echoerr "clang-format not installed"
        return
    endif

    if !empty(findfile('.clang-format', expand('%:p:h') . ';'))
        let cursor_pos = getpos('.')
        :%!clang-format
        call setpos('.', cursor_pos)
    elseif quiet != "quiet"
        :echo ".clang-format file not found!"
    endif
endfunction

" Run clang format whenever a supported file format is used.
" (C, C++, C#, Java, JavaScript, Object-C, Object-C++, ProtoBuf)
if executable('clang-format')
    augroup clangformat_on_save
        autocmd!
        autocmd BufWritePre *.c,*.cpp,*.cc,*.h,*.hpp,*.inl :call ClangFormatBuffer("quiet")
        autocmd BufWritePre *.vert,*.frag :call ClangFormatBuffer("quiet")
        autocmd BufWritePre *.cs :call ClangFormatBuffer("quiet")
        autocmd BufWritePre *.java :call ClangFormatBuffer("quiet")
        autocmd BufWritePre *.js :call ClangFormatBuffer("quiet")
        autocmd BufWritePre *.m,*.mm :call ClangFormatBuffer("quiet")
    augroup END
endif

" Map CTRL-d (eg visual studio CTRL+K CTRL+D) to format.
let exts = ['c', 'cpp', 'cc', 'h', 'hpp', 'inl', 'vert', 'frag', 'cs', 'java', 'js', 'm', 'mm']

if index(exts, expand('%:e')) > -1
  nnoremap <C-d> :call ClangFormatBuffer("")
endif
