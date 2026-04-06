#!/bin/bash
set -e

# Ensure Solr home exists
mkdir -p /var/solr/data
chown -R solr:solr /var/solr

# Start Solr in background for setup
solr start

echo "Waiting for Solr..."
until curl -s http://localhost:8983/solr >/dev/null; do
  sleep 2
done

# Create core (only if it doesn't exist)
if [ ! -d /var/solr/data/vector_test ]; then
  solr create_core -c vector_test -d /opt/solr/server/solr/configsets/vector_config
fi

sleep 3

# Index test data
curl http://localhost:8983/solr/vector_test/update?commit=true \
  -H "Content-Type: application/json" -d '
[
  {"id":"1","title":"Red shoes","embedding":[1.0,0.0,0.0,0.0]},
  {"id":"2","title":"Blue shoes","embedding":[0.9,0.1,0.0,0.0]},
  {"id":"3","title":"Laptop computer","embedding":[0.0,1.0,0.0,0.0]},
  {"id":"4","title":"Gaming laptop","embedding":[0.0,0.9,0.1,0.0]},
  {"id":"5","title":"Banana fruit","embedding":[0.0,0.0,1.0,0.0]}
]'

echo "Starting Solr in foreground..."

# Stop background Solr
solr stop

# Start Solr in foreground (PID 1)
exec solr -f