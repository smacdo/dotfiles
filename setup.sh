#!/bin/bash
#############################################################################
# Automated installation script
#  - This script will set up common directories, dot files and other system
#    settings
#############################################################################
bin_dir=$HOME/bin

echo "This script will automatically update your system to use common directories, "
echo "various dotfiles (zsh, vimrc, etc) and other assorted goodies. "
echo " "

# Ask the user to confirm before proceeding
read -p "Do you wish to continue? (y|n) "
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    exit 1
fi

# Create common directories
echo "Creating common directories..."

mkdir -vp $HOME/.zsh
mkdir -vp $HOME/.zsh_local
mkdir -vp $HOME/.vim_runtime/backups
mkdir -vp $HOME/.vim_runtime/tmp
mkdir -vp $HOME/projects

# Symlink useful dotfiles
echo "Copying dotfiles..."

rm -i $HOME/.vimrc
ln -sv $bin_dir/.vimrc $HOME

rm -ir $HOME/.vim
ln -sv $bin_dir/.vim $HOME

rm -i $HOME/.bash_profile
ln -sv $bin_dir/.bash_profile $HOME

rm -i $HOME/.bashrc
ln -sv $bin_dir/.bashrc $HOME

rm -i $HOME/.zshrc
ln -sv $bin_dir/.zshrc $HOME

rm -ir $HOME/.zsh
ln -sv $bin_dir/zsh_files $HOME

rm -i $HOME/.dircolors
ln -sv $bin_dir/.dircolors $HOME

rm -i $HOME/.inputrc
ln -sv $bin_dir/.inputrc $HOME

# Install fonts
echo "Installing liberation fonts..."
mkdir -pv $HOME/.fonts/liberation
cp $bin_dir/fonts/liberation/*.ttf $HOME/.fonts/liberation

echo "Installing ubuntu fonts..."
mkdir -pv $HOME/.fonts/ubuntu
cp $bin_dir/fonts/ubuntu/*.ttf $HOME/.fonts/ubuntu

echo "Installing consola fonts..."
mkdir -pv $HOME/.fonts/consola
cp $bin_dir/fonts/consola/*.ttf $HOME/.fonts/consola
