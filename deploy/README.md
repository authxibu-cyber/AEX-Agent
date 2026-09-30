# Deployment — merlinagent.site

VPS: 187.53.134.95 (Ubuntu 26.04, nginx + certbot already serving myscape.site)

- Site root: /var/www/merlinagent (git clone of this repo; docs/ is the web root)
- nginx config: deploy/merlinagent.nginx (installed at
  /etc/nginx/sites-available/merlinagent)
- merlinagent.site + www -> static landing page (docs/index.html)
- /v1/ -> reverse proxy to Merlin gateway on 127.0.0.1:8642 (run
  `merlin-gateway` on the VPS to bring the API online)
- gateway.merlinagent.site -> full gateway proxy (add DNS A record first)
- SSL: Let's Encrypt via `certbot --nginx` (auto-renews)

Update procedure:
    ssh root@187.53.134.95 "git -C /var/www/merlinagent pull --ff-only"
