# Render entrypoint for the consolidated gateway. Static assets are built and
# copied into the image by scripts/build_frontends.py before image creation.
# Production backends are intentionally absent until their deployment
# prerequisites and resource use are verified in config/projects/*.json.
FROM nginx:1.29-alpine
WORKDIR /usr/share/nginx/html
COPY dist/ /usr/share/nginx/html/
COPY infrastructure/nginx/generated/render.conf /etc/nginx/conf.d/default.conf
ENV PORT=10000
EXPOSE 10000
HEALTHCHECK --interval=20s --timeout=4s --retries=5 CMD wget -q -O /dev/null http://127.0.0.1:${PORT}/healthz || exit 1
CMD ["/bin/sh", "-c", "sed -i \"s/listen 8080;/listen ${PORT};/\" /etc/nginx/conf.d/default.conf && exec nginx -g 'daemon off;'" ]
