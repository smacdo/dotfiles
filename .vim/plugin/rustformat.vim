" This function when called will save the current buffer, run `rustfmt` against
" it and then reload the buffer. If rustfmt fails or produces output the output
" will be displayed to the user in a new split pane.
function RustFormatBuffer(verbosity)
    if !executable('rustfmt')
        echoerr "rustfmt not installed"
        return
    endif

    " Save the file to force changes to be written out prior to formatting.
    write

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
      e
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
      end
    end
endfunction

" If rustfmt is found then apply rust formatting anytime a buffer is saved.
" (a buffer with an appropriate file extension).
if executable('rustfmt')
    augroup rustformat_on_save
        autocmd!
        autocmd BufWritePre *.rs :call RustFormatBuffer("quiet")
    augroup END
endif

" Map CTRL-d (eg visual studio CTRL+K CTRL+D) to rust format.
let exts = ['rs']

if index(exts, expand('%:e')) > -1
  nnoremap <C-d> :call RustFormatBuffer("")
endif
