package com.buy01.order_service;

import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.beans.factory.annotation.Autowired;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import org.springframework.web.server.ResponseStatusException;

import com.buy01.order_service.service.OrderService;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT, properties = "eureka.client.enabled=false")
class OrderServiceApplicationTests {

    @org.springframework.boot.test.web.server.LocalServerPort
    private int port;

	// The real fallback must keep the module bootable without fabricating orders.
	@Autowired
	private OrderService orderService;

	@Test
	void contextLoads() {
        assertThatThrownBy(() -> orderService.createOrder(null, "key", null))
                .isInstanceOf(ResponseStatusException.class);
	}

    @Test
    void runningOrdersApiExplicitlyRejectsCreationRatherThanPretendingToPersist() throws Exception {
        var request = java.net.http.HttpRequest.newBuilder(java.net.URI.create("http://localhost:" + port + "/orders"))
            .header("Content-Type", "application/json").header("Idempotency-Key", "live-check")
            .header("X-User-Id", "client").header("X-User-Roles", "CLIENT")
            .POST(java.net.http.HttpRequest.BodyPublishers.ofString("""
                {"items":[{"productId":"p1","quantity":1}],"shippingAddress":{
                "fullName":"Jane","phone":"123","street":"Street","city":"City","postalCode":"100","country":"Morocco"},
                "paymentMethod":"CASH_ON_DELIVERY"}
                """)).build();
        var response = java.net.http.HttpClient.newHttpClient().send(request, java.net.http.HttpResponse.BodyHandlers.ofString());
        org.assertj.core.api.Assertions.assertThat(response.statusCode()).isEqualTo(503);
        org.assertj.core.api.Assertions.assertThat(response.body()).contains("Orders Service implementation is not available yet");
    }

    @Test
    void restClientAgainstRunningOrdersApiDoesNotProduceAReceipt() {
        var client = new com.buy01.order_service.client.OrdersClient("http://localhost:" + port + "/orders");
        var address = new com.buy01.order_service.dtos.common.ShippingAddressDto("Jane", "123", "Street", "City", "100", "Morocco");
        var request = new com.buy01.order_service.dtos.req.CreateOrderRequest(
            java.util.List.of(new com.buy01.order_service.dtos.req.OrderItemRequest("p1", 1)), address,
            com.buy01.order_service.models.PaymentMethod.CASH_ON_DELIVERY);
        assertThatThrownBy(() -> client.create(request, "live-client-check",
            new com.buy01.order_service.security.AuthenticatedUser("client", java.util.List.of("CLIENT"))))
            .isInstanceOf(com.buy01.order_service.exception.UpstreamServiceException.class);
    }

}
