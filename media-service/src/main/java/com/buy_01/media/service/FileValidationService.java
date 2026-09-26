package com.buy_01.media.service;

import java.io.IOException;
import java.util.List;

import org.apache.tika.Tika;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import com.buy_01.media.exception.InvalidFileException;

@Service
public class FileValidationService {

    private static final long MAX_FILE_SIZE = 2 * 1024 * 1024; // 2MB
    private static final List<String> ALLOWED_MIME_TYPES = List.of(
            "image/jpeg", "image/png", "image/webp", "image/gif"
    );

    private final Tika tika = new Tika();

    public void validate(MultipartFile file) {
        if (file == null || file.isEmpty()) {
            throw new InvalidFileException("Uploaded file cannot be empty");
        }

        // 1. Validate File Size
        if (file.getSize() > MAX_FILE_SIZE) {
            throw new InvalidFileException("File size exceeds 2MB limit");
        }

        // 2. Validate Genuine MIME Type using Apache Tika
        try {
            String detectedType = tika.detect(file.getInputStream());
            if (!ALLOWED_MIME_TYPES.contains(detectedType)) {
                throw new InvalidFileException("Invalid file type: " + detectedType + ". Only images are allowed.");
            }
        } catch (IOException e) {
            throw new RuntimeException("Failed to analyze file MIME type", e);
        }
    }
}