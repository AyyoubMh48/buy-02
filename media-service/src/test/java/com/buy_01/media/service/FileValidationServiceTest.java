package com.buy_01.media.service;

import com.buy_01.media.exception.InvalidFileException;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockMultipartFile;

import static org.assertj.core.api.Assertions.assertThatCode;
import static org.junit.jupiter.api.Assertions.assertThrows;

class FileValidationServiceTest {

    private FileValidationService validationService;

    @BeforeEach
    void setUp() {
        validationService = new FileValidationService();
    }

    @Test
    void validate_NullFile_ThrowsException() {
        assertThrows(InvalidFileException.class, () -> validationService.validate(null));
    }

    @Test
    void validate_EmptyFile_ThrowsException() {
        MockMultipartFile emptyFile = new MockMultipartFile("file", "empty.png", "image/png", new byte[0]);
        assertThrows(InvalidFileException.class, () -> validationService.validate(emptyFile));
    }

    @Test
    void validate_FileExceeds2MB_ThrowsException() {
        byte[] oversizedBytes = new byte[2 * 1024 * 1024 + 1];
        MockMultipartFile largeFile = new MockMultipartFile("file", "large.png", "image/png", oversizedBytes);
        assertThrows(InvalidFileException.class, () -> validationService.validate(largeFile));
    }

    @Test
    void validate_DisallowedMimeType_ThrowsException() {
        byte[] pdfBytes = "%PDF-1.4 header and content".getBytes();
        MockMultipartFile pdfFile = new MockMultipartFile("file", "document.pdf", "application/pdf", pdfBytes);
        assertThrows(InvalidFileException.class, () -> validationService.validate(pdfFile));
    }

    @Test
    void validate_ValidPng_Success() {
        byte[] pngBytes = new byte[]{(byte) 0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A, 0x00, 0x00};
        MockMultipartFile pngFile = new MockMultipartFile("file", "valid.png", "image/png", pngBytes);
        assertThatCode(() -> validationService.validate(pngFile)).doesNotThrowAnyException();
    }
}
