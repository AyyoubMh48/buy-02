package com.buy01.user_service.client;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestClientResponseException;

import com.buy01.user_service.dto.external.MediaMetadataResponse;
import com.buy01.user_service.exception.BadRequestException;
import com.buy01.user_service.exception.UpstreamServiceException;

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
                    .uri("/{id}/metadata", mediaId)
                    .retrieve()
                    .body(MediaMetadataResponse.class);
        } catch (RestClientResponseException ex) {
            if (ex.getStatusCode().value() == 404) {
                throw new BadRequestException("Media not found: " + mediaId);
            }
            throw new UpstreamServiceException(
                    "Media Service returned " + ex.getStatusCode() + " while resolving media " + mediaId);
        } catch (RestClientException ex) {
            throw new UpstreamServiceException(
                    "Media Service is unreachable while resolving media " + mediaId);
        }
    }
}