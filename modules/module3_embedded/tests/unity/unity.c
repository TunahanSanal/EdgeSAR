/**
 * @file unity.c
 * @brief Unity Test Runner Implementation.
 */

#include "unity.h"
#include <stdio.h>

Unity_t Unity;

void UnityBegin(const char *filename)
{
    Unity.numberOfTests = 0U;
    Unity.testFailures = 0U;
    Unity.testIgnores = 0U;
    Unity.currentTestName = "";
    Unity.currentTestLineNumber = 0U;

    printf("\n========================================================\n");
    printf(" Unity Test Suite: %s\n", filename);
    printf("========================================================\n");
}

int UnityEnd(void)
{
    printf("--------------------------------------------------------\n");
    printf(" %u Tests | %u Failures | %u Ignored\n",
           Unity.numberOfTests, Unity.testFailures, Unity.testIgnores);

    if (Unity.testFailures == 0U) {
        printf(" OK: ALL TESTS PASSED (100%% VERIFIED)\n");
        printf("========================================================\n\n");
        return 0;
    } else {
        printf(" FAIL: %u TEST(S) FAILED\n", Unity.testFailures);
        printf("========================================================\n\n");
        return 1;
    }
}

void UnityTestPass(void)
{
    /* Individual assertions pass silently */
}

void UnityTestFail(const char *message, uint32_t lineNumber)
{
    Unity.testFailures++;
    printf(" [FAIL] %s (Line %u): %s\n",
           Unity.currentTestName, lineNumber, (message != NULL) ? message : "");
}
