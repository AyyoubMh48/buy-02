package com.buy01.product_service.security;

import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;
 
@Retention(RetentionPolicy.RUNTIME)

// ths annotation Retention is responsible for specifying how long annotations with the 
// annotated type are to be retained.
// in this case, the annotation will be available at runtime, which is necessary for reflection-based processing.

@Target(ElementType.PARAMETER)
// the annotation Target is responsible for specifying the kinds of program element
//  to which an annotation type is applicable.

public @interface CurrentUser {



//  required = true (default) throws a 401 err if l headers are khawyin or invalid.
    boolean requiired() default true;
}
