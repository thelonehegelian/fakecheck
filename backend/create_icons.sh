#!/bin/bash
# Quick script to create placeholder icons using ImageMagick (if installed)
# If you don't have ImageMagick, just create simple PNG files manually

if command -v convert &> /dev/null; then
  # Create simple colored icons with "FC" text
  convert -size 16x16 xc:#667eea -fill white -pointsize 10 -gravity center -annotate +0+0 'FC' icon16.png
  convert -size 48x48 xc:#667eea -fill white -pointsize 32 -gravity center -annotate +0+0 'FC' icon48.png
  convert -size 128x128 xc:#667eea -fill white -pointsize 88 -gravity center -annotate +0+0 'FC' icon128.png
  echo "Icons created!"
else
  echo "ImageMagick not installed. Please create icons manually or use an online tool."
fi
