package com.buy01.user_service.dto;

import com.buy01.user_service.model.Role;
import jakarta.validation.constraints.AssertTrue;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import lombok.Data;

@Data
public class RegisterDto {

    @Size(min = 2, max = 50, message = "Username must be between 2 and 50 characters")
    @Pattern(regexp = "^[\\p{L}0-9_.'\\- @]+$", message = "Username contains invalid characters")
    private String username;

    @Size(min = 2, max = 50, message = "Full name must be between 2 and 50 characters")
    @Pattern(regexp = "^[\\p{L}0-9_.'\\- @]+$", message = "Full name contains invalid characters")
    private String fullName;

    @NotBlank(message = "Email is required")
    @Email(message = "Invalid email format")
    @Size(max = 254, message = "Email cannot exceed 254 characters")
    @Pattern(regexp = "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$", message = "Email format is invalid")
    private String email;

    @NotBlank(message = "Password is required")
    @Size(min = 6, max = 72, message = "Password must be between 6 and 72 characters")
    private String password;

    @NotNull(message = "Role is required")
    private Role role;

    @Size(max = 2048, message = "Avatar URL or media ID is too long")
    @Pattern(regexp = "^(https?://[^\\s<>\"'{}|\\\\^`]+|[a-zA-Z0-9_-]+)?$", message = "Avatar must be a valid media ID or HTTP/HTTPS URL")
    private String avatarUrl;

    @AssertTrue(message = "Either username or full name must be provided")
    public boolean isUsernameOrFullNamePresent() {
        return (username != null && !username.isBlank()) || (fullName != null && !fullName.isBlank());
    }

    public String getUsername() {
        if (username != null && !username.isBlank()) {
            return username;
        }
        return fullName;
    }
}