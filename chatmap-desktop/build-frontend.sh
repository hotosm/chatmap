cd ../chatmap-ui && \
yarn build  && \
cd ../chatmap-desktop && \
cp -R ../chatmap-ui/build/* public/

