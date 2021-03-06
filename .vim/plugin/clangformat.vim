" Simple clang format function taken from a Stack Overflow answer.
" Ref: https://vi.stackexchange.com/a/22985
"
" This function when called will search for a '.clang-format' file in the
" current directory or a parent directory. If it finds one then it will save the
" cursor position, replace the buffer with clang format results and finally
" restore the cursor position.
function ClangFormatBuffer(verbosity)
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
autocmd BufWritePre *.h,*.hpp,*.c,*.cpp,*.cc :call ClangFormatBuffer("quiet")
autocmd BufWritePre *.vert,*.frag :call ClangFormatBuffer("quiet")
autocmd BufWritePre *.cs :call ClangFormatBuffer("quiet")
autocmd BufWritePre *.java :call ClangFormatBuffer("quiet")
autocmd BufWritePre *.js :call ClangFormatBuffer("quiet")
autocmd BufWritePre *.m,*.mm :call ClangFormatBuffer("quiet")

" Map CTRL-d (eg visual studio CTRL+K CTRL+D) to format.
nnoremap <C-d> :call ClangFormatBuffer("")
