cd ../chatmap-ui && \
VITE_ENABLE_LIVE=1 yarn build  && \
cd ../chatmap-desktop && \
cp -R ../chatmap-ui/build/* public/

