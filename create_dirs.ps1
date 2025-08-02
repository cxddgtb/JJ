# 创建项目目录结构
New-Item -ItemType Directory -Path .\data -Force
New-Item -ItemType Directory -Path .\models -Force
New-Item -ItemType Directory -Path .\scripts -Force
New-Item -ItemType Directory -Path .\.github\workflows -Force
Write-Host "目录结构创建完成!"