#!/bin/bash
#############################################################################
# Automated installation script
#  - This script will set up common directories, dot files and other system
#    settings
#############################################################################
echo "This script will automatically update your system to use common directories, "
echo "various dotfiles (zsh, vimrc, etc) and other assorted goodies. "
echo " "

# Ask the user to confirm before proceeding
read -p "Do you wish to continue? (y|n) "
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    exit 1
fi

exit


rm -frv $HOME/{.zshrc,.aliases,.vim,.vimrc}
cd $HOME
ln -s $HOME/bin/.zshrc
ln -s $HOME/bin/.vim
ln -s $HOME/bin/.vimrc
ln -s $HOME/bin/.zsh_local
ln -s $HOME/bin/zsh_functions/generic_functions.zsh  $HOME/bin/.zsh_local/
ln -s $HOME/bin/zsh_functions/aliases.zsh $HOME/bin/.zsh_local/

echo "Cloning files for oh-my-zsh"
git clone git://github.com/robbyrussell/oh-my-zsh.git ~/.oh-my-zsh

echo "Creating standard dirs"
for i in $HOME/projects $HOME/local $HOME/.vim_backup $HOME/.vim_runtime ; do 
   if [ ! -e ${i} ]; then
        mkdir $i >& /dev/null
   fi
done

echo "Standard coding projects go in $HOME/projects"
echo "eclipse code goes in $HOME/workspace"
echo "any $HOME install goes into $HOME/local and binary is symlinked in $HOME/bin/private"
