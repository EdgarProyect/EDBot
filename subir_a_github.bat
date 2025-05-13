@echo off
echo --------------------------------------
echo Subiendo bot a GitHub...
echo --------------------------------------

git init
git add .
git commit -m "Primer commit del bot"
git branch -M main

REM Reemplaza el siguiente enlace por tu repositorio real:
git remote add origin https://github.com/EdgarProyect/edbot.git

git push -u origin main

pause
