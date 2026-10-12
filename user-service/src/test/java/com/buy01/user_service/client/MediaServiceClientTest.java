package com.buy01.user_service.client;

import static org.assertj.core.api.Assertions.assertThat;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withStatus;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestClient;

import com.buy01.user_service.exception.BadRequestException;
import com.buy01.user_service.exception.UpstreamServiceException;

class MediaServiceClientTest {

    private MockRestServiceServer server;
    private MediaServiceClient client;

    @BeforeEach
    void setUp() {
        RestClient.Builder builder = RestClient.builder();
        server = MockRestServiceServer.bindTo(builder).build();
        client = new MediaServiceClient(builder, "http://media");
    }

    @Test
    void fetchMetadata_returnsBody() {
        server.expect(requestTo("http://media/m1/metadata"))
                .andRespond(withSuccess(
                        "{\"id\":\"m1\",\"filename\":\"f\",\"contentType\":\"image/png\",\"url\":\"u\",\"size\":1,\"uploaderId\":\"owner\"}",
                        MediaType.APPLICATION_JSON));

        var response = client.fetchMetadata("m1");

        assertThat(response.id()).isEqualTo("m1");
        assertThat(response.uploaderId()).isEqualTo("owner");
    }

    @Test
    void fetchMetadata_notFound_throwsBadRequest() {
        server.expect(requestTo("http://media/m1/metadata"))
                .andRespond(withStatus(HttpStatus.NOT_FOUND));

        assertThrows(BadRequestException.class, () -> client.fetchMetadata("m1"));
    }

    @Test
    void fetchMetadata_serverError_throwsUpstreamService() {
        server.expect(requestTo("http://media/m1/metadata"))
                .andRespond(withStatus(HttpStatus.INTERNAL_SERVER_ERROR));

        assertThrows(UpstreamServiceException.class, () -> client.fetchMetadata("m1"));
    }
}