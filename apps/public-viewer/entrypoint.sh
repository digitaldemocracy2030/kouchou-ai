#!/bin/sh
# 起動時に全て削除した上でbuildしなおす
if [ -d ".next" ]; then
  rm -rf .next
fi  
# build時にAPIサーバーを参照するため、APIサーバーの起動を待ってからbuildを行う
npm run build
exec npm run start