cd .. && \
VITE_ENABLE_LIVE=1 yarn build  && \
cd electron-app && \
cp -R ../build/* public/

