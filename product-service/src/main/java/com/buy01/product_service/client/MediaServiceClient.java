package com.buy01.product_service.client;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestClientResponseException;

import com.buy01.product_service.dtos.external.MediaMetadataResponse;
import com.buy01.product_service.exceptionsHandler.BadRequest;
import com.buy01.product_service.exceptionsHandler.UpstreamServiceException;

/**
 * Calls Media Service directly by its Docker Compose service name + fixed
 * port. Eureka discovery is NOT used here because Media Service currently
 * runs with eureka.client.enabled: false and never registers, so a
 * load-balanced/discovery-based client would have nothing to resolve.
 * Docker's built-in DNS already resolves "media-service" to the right
 * container on the shared network, so a plain fixed base URL works fine.
 */
@Component
public class MediaServiceClient {

    private final RestClient restClient;

    public MediaServiceClient(RestClient.Builder builder,
            @Value("${media-service.base-url}") String baseUrl) {
        this.restClient = builder.baseUrl(baseUrl).build();
    }

    public MediaMetadataResponse fetchMetadata(String mediaId) {
        try {
            return restClient.get()
                    .uri("/{id}", mediaId)
                    .accept(MediaType.APPLICATION_JSON)
                    .retrieve()
                    .body(MediaMetadataResponse.class);
        } catch (RestClientResponseException ex) {
            if (ex.getStatusCode().value() == 404) {
                throw new BadRequest("Media not found: " + mediaId);
            }
            throw new UpstreamServiceException(
                    "Media Service returned " + ex.getStatusCode() + " while resolving media " + mediaId);
        } catch (RestClientException ex) {
            throw new UpstreamServiceException(
                    "Media Service is unreachable while resolving media " + mediaId);
        }
    }
}
