package com.buy01.user_service.exception;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.validation.BeanPropertyBindingResult;
import org.springframework.validation.FieldError;
import org.springframework.validation.ObjectError;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.core.MethodParameter;
import org.springframework.http.converter.HttpMessageNotReadableException;

class GlobalExceptionHandlerTest {

    private final GlobalExceptionHandler handler = new GlobalExceptionHandler();

    @Test
    void handleEmailExists_returnsConflict() {
        var response = handler.handleEmailExists(new EmailAlreadyExistsException("dup"));

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.CONFLICT);
        assertThat(response.getBody()).containsEntry("message", "dup");
    }

    @Test
    void handleInvalidCredentials_returnsUnauthorized() {
        var response = handler.handleInvalidCredentials(new InvalidCredentialsException("bad"));

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.UNAUTHORIZED);
    }

    @Test
    void handleUnauthorized_returnsUnauthorized() {
        var response = handler.handleUnauthorized(new UnauthorizedException("no"));

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.UNAUTHORIZED);
    }

    @Test
    void handleBadRequest_returnsBadRequest() {
        var response = handler.handleBadRequest(new BadRequestException("bad"));

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.BAD_REQUEST);
    }

    @Test
    void handleUpstreamService_returnsServiceUnavailable() {
        var response = handler.handleUpstreamService(new UpstreamServiceException("down"));

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.SERVICE_UNAVAILABLE);
    }

    @Test
    void handleUserNotFound_returnsNotFound() {
        var response = handler.handleUserNotFound(new UserNotFoundException("missing"));

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.NOT_FOUND);
    }

    @Test
    void handleHttpMessageNotReadable_returnsBadRequest() {
        var response = handler.handleHttpMessageNotReadable(
                mock(HttpMessageNotReadableException.class));

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.BAD_REQUEST);
        assertThat(response.getBody()).containsEntry("error", "Bad Request");
    }

    @Test
    void handleValidationException_collectsFieldAndGlobalErrors() throws Exception {
        BeanPropertyBindingResult binding = new BeanPropertyBindingResult(new Object(), "target");
        binding.addError(new FieldError("target", "email", "Invalid email format"));
        binding.addError(new ObjectError("target", "Global problem"));
        var ex = new MethodArgumentNotValidException(mock(MethodParameter.class), binding);

        var response = handler.handleValidationException(ex);

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.BAD_REQUEST);
        assertThat(response.getBody()).containsEntry("error", "Validation Failed");
        @SuppressWarnings("unchecked")
        var fields = (java.util.Map<String, Object>) response.getBody().get("fields");
        assertThat(fields).containsKey("email").containsKey("target");
    }
}