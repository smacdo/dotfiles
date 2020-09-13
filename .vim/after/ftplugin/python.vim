setlocal expandtab     " Always use spaces instead of tabs in python.
setlocal shiftwidth=4  " 4 spaces when auto indenting, >> << ==
setlocal softtabstop=4 " Treat 4 spaces as a tab when hitting tab, deleting etc.

syn keyword pythonDecorator True None False self

"Delete trailing white space, useful for Python ;)
func! DeleteTrailingWS()
  exe "normal mz"
  %s/\s\+$//ge
  exe "normal `z"
endfunc
autocmd BufWrite *.py :call DeleteTrailingWS()

