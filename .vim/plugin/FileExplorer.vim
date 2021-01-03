" Make vim's netrw (file explorer) open/close when CTRL+O is pressed. Based on
" code from Stack Overflow answers from:
" Ref: https://stackoverflow.com/a/51199145
function ToggleVExplorer()
    " If the netrw explorer window is opened, close it. Otherwise open it.
    if exists("t:expl_buf_num")
        " Get the window id of netrw explorer (if open, otherwise is -1). 
        let expl_win_num = bufwinnr(t:expl_buf_num)

        " Get the current window number.
        let cur_win_num = winnr()

        " If there exists an open netrw explorer window, keep switching windows until we switch
        " into the netrw window.
        if expl_win_num != -1
            while expl_win_num != cur_win_num
                " Switch to the next window.
                exec "wincmd w"

                " Get this window's number.
                let cur_win_num = winnr()
            endwhile

            " With the loop having ended, the current window is the netrw explorer window.
            " Close it.
            close
        endif

        " ? Not sure...
        unlet t:expl_buf_num
    else
        " Open the netrw explorer window.
        Vexplore

        " ?
        let t:expl_buf_num = bufnr("%")
    endif
endfunction

map <silent> <C-O> :call ToggleVExplorer()<CR>

