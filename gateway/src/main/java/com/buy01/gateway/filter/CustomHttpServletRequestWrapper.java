package com.buy01.gateway.filter;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletRequestWrapper;

import java.util.*;

public class CustomHttpServletRequestWrapper extends HttpServletRequestWrapper {

    private final Map<String, String> customHeaders = new HashMap<>();

    public CustomHttpServletRequestWrapper(HttpServletRequest request) {
        super(request);
    }

    public void putHeader(String name, String value) {
        customHeaders.put(name, value);
    }

    @Override
    public String getHeader(String name) {
        String customHeader = customHeaders.get(name);

        if (customHeader != null) {
            return customHeader;
        }

        return super.getHeader(name);
    }

    @Override
    public Enumeration<String> getHeaders(String name) {
        String customHeader = customHeaders.get(name);

        if (customHeader != null) {
            return Collections.enumeration(List.of(customHeader));
        }

        return super.getHeaders(name);
    }

    @Override
    public Enumeration<String> getHeaderNames() {
        Set<String> headerNames = new HashSet<>(customHeaders.keySet());

        Enumeration<String> originalHeaders = super.getHeaderNames();

        while (originalHeaders.hasMoreElements()) {
            headerNames.add(originalHeaders.nextElement());
        }

        return Collections.enumeration(headerNames);
    }
}