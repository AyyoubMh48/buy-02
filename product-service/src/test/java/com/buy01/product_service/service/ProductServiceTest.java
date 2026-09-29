package com.buy01.product_service.service;

import com.buy01.product_service.client.MediaServiceClient;
import com.buy01.product_service.exceptionsHandler.ResourceNotFoundException;
import com.buy01.product_service.exceptionsHandler.UnauthorizedException;
import com.buy01.product_service.models.Product;
import com.buy01.product_service.repository.ProductRepository;
import com.buy01.product_service.security.AuthenticatedUser;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.kafka.core.KafkaTemplate;

import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class ProductServiceTest {

    @Mock
    private ProductRepository productRepository;

    @Mock
    private MediaServiceClient mediaServiceClient;

    @Mock
    private KafkaTemplate<String, Object> kafkaTemplate;

    @InjectMocks
    private ProductService productService;

    private AuthenticatedUser sellerUser;
    private AuthenticatedUser buyerUser;
    private Product sampleProduct;

    @BeforeEach
    void setUp() {
        sellerUser = new AuthenticatedUser("seller-123", List.of("SELLER"));
        buyerUser = new AuthenticatedUser("buyer-456", List.of("CLIENT"));
        sampleProduct = Product.builder()
                .id("prod-1")
                .name("Sample Item")
                .description("Sample Description")
                .price(49.99)
                .quantity(10)
                .ownerId("seller-123")
                .mediaIds(new String[]{"img-1"})
                .images(new String[]{"https://cdn.example.com/img-1.png"})
                .build();
    }

    @Test
    void findAproduuct_NotFound_ThrowsResourceNotFoundException() {
        when(productRepository.findById("non-existent")).thenReturn(Optional.empty());

        assertThrows(ResourceNotFoundException.class, () -> productService.findAproduuct("non-existent"));
    }

    @Test
    void findMyProduct_WhenOwner_ReturnsProduct() {
        when(productRepository.findById("prod-1")).thenReturn(Optional.of(sampleProduct));

        Product product = productService.findMyProduct("prod-1", sellerUser);

        assertThat(product).isNotNull();
        assertThat(product.getId()).isEqualTo("prod-1");
        assertThat(product.getOwnerId()).isEqualTo("seller-123");
    }

    @Test
    void findMyProduct_WhenNotOwner_ThrowsUnauthorizedException() {
        when(productRepository.findById("prod-1")).thenReturn(Optional.of(sampleProduct));

        assertThrows(UnauthorizedException.class, () -> productService.findMyProduct("prod-1", buyerUser));
    }

    @Test
    void isSeller_WhenUserIsSeller_DoesNotThrow() {
        assertDoesNotThrow(() -> productService.isSeller(sellerUser));
    }

    @Test
    void isSeller_WhenUserIsNotSeller_ThrowsUnauthorizedException() {
        assertThrows(UnauthorizedException.class, () -> productService.isSeller(buyerUser));
    }
}
