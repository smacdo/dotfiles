" This function when called will save the current buffer, run `rustfmt` against
" it and then reload the buffer. If rustfmt fails or produces output the output
" will be displayed to the user in a new split pane.
function RustFormatBuffer(verbosity)
  " Skip formatting if disabled.
  if exists("g:no_format") && g:fo_format
    return
  endif

  " Only format if rustfmt is installed.
  if !executable('rustfmt')
    if a:verbosity != "quiet"
      echoerr "rustfmt not installed"
    endif

    return
  endif

  " Save the current window and cursor position for later restoration.
  let l:current_window = winnr()
  let cursor_pos = getpos('.')

  " Run `rustfmt` by passing the current buffer contents to stdin, and then
  " replacing the buffer with the contents of stdout (unless there was a
  " problem).
  %!rustfmt

  " Check for any errors returned from the formatter and do not reload the
  " file if so.
  " TODO: Only do this if not quiet. In quiet mode merely undo the changes.
  if v:shell_error > 0
    if a:verbosity == "quiet"
      echoerr "rustfmt exited with non-zero error code - unformatted file will be saved"
      undo
    else
      echoerr "rustfmt exited with non-zero error code - call :undo to restore"
    endif
  endif

  " Restore the old cursor position to minimize editor churn on the user.
  call setpos('.', cursor_pos)
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
