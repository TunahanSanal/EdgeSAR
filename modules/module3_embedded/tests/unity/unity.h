/**
 * @file unity.h
 * @brief Lightweight Unity Embedded C Unit Testing Framework.
 * @details Minimal self-contained implementation conforming to standard Unity API.
 */

#ifndef UNITY_FRAMEWORK_H
#define UNITY_FRAMEWORK_H

#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <math.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    uint32_t numberOfTests;
    uint32_t testFailures;
    uint32_t testIgnores;
    const char *currentTestName;
    uint32_t currentTestLineNumber;
} Unity_t;

extern Unity_t Unity;

void setUp(void);
void tearDown(void);

void UnityBegin(const char *filename);
int  UnityEnd(void);
void UnityTestPass(void);
void UnityTestFail(const char *message, uint32_t lineNumber);

#define UNITY_BEGIN() UnityBegin(__FILE__)
#define UNITY_END()   UnityEnd()

#define RUN_TEST(func) \
    do { \
        Unity.numberOfTests++; \
        Unity.currentTestName = #func; \
        Unity.currentTestLineNumber = __LINE__; \
        setUp(); \
        func(); \
        tearDown(); \
    } while (0)

#define TEST_ASSERT(condition) \
    do { \
        if (!(condition)) { \
            UnityTestFail("Expression Evaluated to FALSE: " #condition, __LINE__); \
            return; \
        } else { \
            UnityTestPass(); \
        } \
    } while (0)

#define TEST_ASSERT_TRUE(condition)  TEST_ASSERT(condition)
#define TEST_ASSERT_FALSE(condition) TEST_ASSERT(!(condition))

#define TEST_ASSERT_EQUAL_INT(expected, actual) \
    do { \
        if ((expected) != (actual)) { \
            char msg[128]; \
            (void)snprintf(msg, sizeof(msg), "Expected %ld Was %ld", (long)(expected), (long)(actual)); \
            UnityTestFail(msg, __LINE__); \
            return; \
        } else { \
            UnityTestPass(); \
        } \
    } while (0)

#define TEST_ASSERT_EQUAL_UINT(expected, actual) \
    do { \
        if ((expected) != (actual)) { \
            char msg[128]; \
            (void)snprintf(msg, sizeof(msg), "Expected %lu Was %lu", (unsigned long)(expected), (unsigned long)(actual)); \
            UnityTestFail(msg, __LINE__); \
            return; \
        } else { \
            UnityTestPass(); \
        } \
    } while (0)

#define TEST_ASSERT_FLOAT_WITHIN(delta, expected, actual) \
    do { \
        float diff = fabsf((float)(expected) - (float)(actual)); \
        if (diff > (float)(delta)) { \
            char msg[128]; \
            (void)snprintf(msg, sizeof(msg), "Expected %f Was %f (diff %f > delta %f)", \
                           (double)(expected), (double)(actual), (double)diff, (double)(delta)); \
            UnityTestFail(msg, __LINE__); \
            return; \
        } else { \
            UnityTestPass(); \
        } \
    } while (0)

#define TEST_ASSERT_NULL(pointer) \
    do { \
        if ((pointer) != NULL) { \
            UnityTestFail("Expected NULL", __LINE__); \
            return; \
        } else { \
            UnityTestPass(); \
        } \
    } while (0)

#define TEST_ASSERT_NOT_NULL(pointer) \
    do { \
        if ((pointer) == NULL) { \
            UnityTestFail("Expected Non-NULL", __LINE__); \
            return; \
        } else { \
            UnityTestPass(); \
        } \
    } while (0)

#ifdef __cplusplus
}
#endif

#endif /* UNITY_FRAMEWORK_H */
