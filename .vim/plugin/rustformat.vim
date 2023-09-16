" Simple clang format function taken from a Stack Overflow answer.
" Ref: https://vi.stackexchange.com/a/22985
"
" This function when called will search for a '.clang-format' file in the
" current directory or a parent directory. If it finds one then it will save the
" cursor position, replace the buffer with clang format results and finally
" restore the cursor position.
function RustFormatBuffer(verbosity)
    if !executable('rustfmt')
        echoerr "rustfmt not installed"
        return
    endif

    " Save the file
    write

    " Make sure there is a cargo file before using cargo format.
    if !empty(findfile('Cargo.toml', expand('%:p:h') . ';'))
        " Save the current window and cursor position for later restoration.
        let current_window = winnr()
        let cursor_pos = getpos('.')

        " Run rustfmt and capture its output in a variable rather than replacing
        " the current buffer. Otherwise `silent! exec ...` should be used.
        let output = system('rustfmt ' . expand('%:p'))

        " Check for any errors returned from the formatter and do not reload the
        " file if so.
        if v:shell_error > 0
          echoerr "rustfmt exited with non-zero error code"
        else
          " Reload the file because the formatter may have altered the contents
          " of the file.
          :e
          redraw

          " Return to the previous cursor position which is either the same or
          " close to the original spot after formatting is applied.
          call setpos('.', cursor_pos)
        end

        " Print the output of the formatter if this function isn't quiet.
        if a:verbosity != "quiet"
          if len(output) > 0
            echoerr "rustfmt had output"

            " Open a new non-file buffer in a vertial split to show the output
            " from rustfmt. Use `normal! ggdG` to delete anything that might be
            " there from a previous run.
            "
            " You can use vsplit for a vertical split, split for horizontal.
            " `belowright` prefix makes the horizontal split open at bottom.
            belowright split __rustfmt__output__
            normal! ggdG
            setlocal buftype=nofile

            " Print the output from rustfmt.
            call append(0, split(output, '\v\n'))
            
            "echoerr output
            "exe current_window . "wincmd w"
          end
        end
    elseif a:verbosity != "quiet"
        " Tell the user that formatting will only happen for Cargo projects.
        " TODO: Is this needed?
        echoerr "Cargo.toml not found - not formatting!"
    endif
endfunction

" Run clang format whenever a supported file format is used.
" (C, C++, C#, Java, JavaScript, Object-C, Object-C++, ProtoBuf)
if executable('cargo')
    augroup rustformat_on_save
        autocmd!
        autocmd BufWritePre *.rs :call RustFormatBuffer("quiet")
    augroup END
endif

" Map CTRL-d (eg visual studio CTRL+K CTRL+D) to format.
let exts = ['rs']

if index(exts, expand('%:e')) > -1
  nnoremap <C-d> :call RustFormatBuffer("")
endif
