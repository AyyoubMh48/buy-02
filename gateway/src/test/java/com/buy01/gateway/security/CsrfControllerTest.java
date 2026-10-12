package com.buy01.gateway.security;

import static org.assertj.core.api.Assertions.assertThat;
import com.buy01.gateway.controller.CsrfController;
import org.junit.jupiter.api.Test;
import org.springframework.security.web.csrf.DefaultCsrfToken;

class CsrfControllerTest {
    @Test
    void exposesTheTokenUsedByTheBrowserForUnsafeRequests() {
        var token = new DefaultCsrfToken("X-XSRF-TOKEN", "_csrf", "test-token");
        assertThat(new CsrfController().csrf(token)).containsOnlyKeys("token").containsEntry("token", "test-token");
    }
}
