package com.buy_01.media.controller;

import java.net.URI;
import java.util.concurrent.TimeUnit;

import org.springframework.http.CacheControl;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

import com.buy_01.media.exception.ForbiddenException;
import com.buy_01.media.exception.UnauthorizedException;
import com.buy_01.media.model.dto.MediaRespDto;
import com.buy_01.media.model.entity.MediaMetaData;
import com.buy_01.media.service.MediaService;

import lombok.RequiredArgsConstructor;

@RestController
@RequestMapping("/media/images")
@RequiredArgsConstructor
public class MediaController {

    private final MediaService mediaService;

    @PostMapping(consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public ResponseEntity<MediaRespDto> uploadImage(
            @RequestParam("file") MultipartFile file,
            @RequestHeader(value = "X-User-Id", required = false) String userId,
            @RequestHeader(value = "X-User-Role", required = false) String userRole,
            @RequestHeader(value = "X-User-Roles", required = false) String userRoles) {

        validateSellerRole(userId, userRole, userRoles, "upload");

        MediaRespDto response = mediaService.uploadImage(file, userId);
        return ResponseEntity.ok(response);
    }

    @GetMapping("/{id}")
    public ResponseEntity<MediaRespDto> getImage(
            @PathVariable String id,
            @RequestHeader(value = HttpHeaders.ACCEPT, required = false) String acceptHeader) {
        MediaMetaData metadata = mediaService.getMetadata(id);

        // If explicitly requested as JSON (e.g. by ProductService RestClient)
        if (acceptHeader != null && acceptHeader.contains(MediaType.APPLICATION_JSON_VALUE)) {
            MediaRespDto response = MediaRespDto.builder()
                    .id(metadata.getId())
                    .url(metadata.getStoragePath())
                    .filename(metadata.getOriginalFilename())
                    .contentType(metadata.getContentType())
                    .size(metadata.getSize())
                    .uploaderId(metadata.getUploaderId())
                    .build();
            return ResponseEntity.ok(response);
        }

        // Serve image with proper HTTP caching headers via redirect to secure Cloudinary CDN
        return ResponseEntity.status(HttpStatus.FOUND)
                .location(URI.create(metadata.getStoragePath()))
                .cacheControl(CacheControl.maxAge(365, TimeUnit.DAYS).cachePublic())
                .header(HttpHeaders.CONTENT_TYPE, metadata.getContentType())
                .build();
    }

    @GetMapping("/{id}/metadata")
    public ResponseEntity<MediaRespDto> getImageMetadata(@PathVariable String id) {
        MediaMetaData metadata = mediaService.getMetadata(id);
        MediaRespDto response = MediaRespDto.builder()
                .id(metadata.getId())
                .url(metadata.getStoragePath())
                .filename(metadata.getOriginalFilename())
                .contentType(metadata.getContentType())
                .size(metadata.getSize())
                .uploaderId(metadata.getUploaderId())
                .build();
        return ResponseEntity.ok(response);
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteImage(
            @PathVariable String id,
            @RequestHeader(value = "X-User-Id", required = false) String userId,
            @RequestHeader(value = "X-User-Role", required = false) String userRole,
            @RequestHeader(value = "X-User-Roles", required = false) String userRoles) {

        validateSellerRole(userId, userRole, userRoles, "delete");
        mediaService.deleteImage(id, userId);
        return ResponseEntity.noContent().build();
    }

    private void validateSellerRole(String userId, String userRole, String userRoles, String action) {
        if (userId == null || userId.isBlank() || "anonymous".equalsIgnoreCase(userId)) {
            throw new UnauthorizedException("Authentication required to " + action + " media.");
        }
        String combinedRoles = ((userRole != null ? userRole : "") + " " + (userRoles != null ? userRoles : "")).toUpperCase();
        if (!combinedRoles.contains("SELLER")) {
            throw new ForbiddenException("Only sellers are permitted to " + action + " media.");
        }
    }
}