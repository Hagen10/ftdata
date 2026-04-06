FROM solr:9.9.0

USER root

# Copy custom config
# COPY config /opt/solr/server/solr/configsets/vector_config/conf

# Copy default configset as base
RUN cp -r /opt/solr/server/solr/configsets/_default /opt/solr/server/solr/configsets/vector_config

# Overwrite ONLY schema
COPY config/managed-schema /opt/solr/server/solr/configsets/vector_config/conf/managed-schema

# Copy init script
COPY entrypoint.sh /entrypoint.sh
# RUN chmod +x /entrypoint.sh

USER solr

ENTRYPOINT ["/entrypoint.sh"]