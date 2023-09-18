" Simple clang format function taken from a Stack Overflow answer.
" Ref: https://vi.stackexchange.com/a/22985
"
" This function when called will search for a '.clang-format' file in the
" current directory or a parent directory. If it finds one then it will save the
" cursor position, replace the buffer with clang format results and finally
" restore the cursor position.
function ClangFormatBuffer(verbosity)
  " Skip formatting if disabled.
  if exists("g:no_format") && g:no_format
    return
  endif

  " Only run clang format if there is a settings file present.
  if empty(findfile('.clang-format', expand('%:p:h') . ';'))
    if a:verbosity != "quiet"
      echoerr "no .clang-format settings file found"
    endif

    return
  endif

  " Make sure clang-format is installed prior to formatting.
  if !executable('clang-format')
    if a:verbosity != "quiet"
      echoerr "no clang-format binary found on path"
    endif

    return
  endif

  " Save the current cursor position prior to formating.
  let cursor_pos = getpos('.')

  " Run `clang-format` by passing the current contents on the buffer to stdin,
  " and then replace the current buffer with `clang-format`'s stdout.
  %!clang-format

  " Check for formatting errors, and undo changes to the buffer.
  if v:shell_error > 0
    if a:verbosity != "quiet"
      echoerr "clang-format exited with non-zero error code"
    endif

    undo
    return
  endif

  " Try to restore the old curosr position to minimize editor churn on the user.
  call setpos('.', cursor_pos)
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
