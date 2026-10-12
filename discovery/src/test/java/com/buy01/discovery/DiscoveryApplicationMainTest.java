package com.buy01.discovery;

import static org.mockito.Mockito.mockStatic;

import org.junit.jupiter.api.Test;
import org.mockito.MockedStatic;
import org.springframework.boot.SpringApplication;

class DiscoveryApplicationMainTest {

    @Test
    void main_delegatesToSpringApplication() {
        try (MockedStatic<SpringApplication> mocked = mockStatic(SpringApplication.class)) {
            DiscoveryApplication.main(new String[]{"--server.port=0"});
            mocked.verify(() -> SpringApplication.run(
                    org.mockito.ArgumentMatchers.eq(DiscoveryApplication.class),
                    org.mockito.ArgumentMatchers.any(String[].class)));
        }
    }
}