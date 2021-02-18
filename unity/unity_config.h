#ifndef UNITY_CONFIG_H
#define UNITY_CONFIG_H

// TODO: include lib.h from kernel headers
// #include "lib/lib.h"

extern void lib_putch(char);

#define NULL 0

#define UNITY_EXCLUDE_SETJMP_H
#define UNITY_EXCLUDE_MATH_H
#define UNITY_EXCLUDE_LIMITS_H
#define UNITY_EXCLUDE_STDINT_H
#define UNITY_EXCLUDE_FLOAT
#define UNITY_EXCLUDE_DOUBLE
#define UNITY_EXCLUDE_STDDEF_H

#define UNITY_INT_WIDTH 32

#define UNITY_OUTPUT_CHAR(a)		lib_putch(a)

// Unity Fixture

#define UNITY_FIXTURE_NO_EXTRAS


#endif /* UNITY_CONFIG_H */
