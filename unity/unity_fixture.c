/* Copyright (c) 2010 James Grenning and Contributed to Unity Project
 * ==========================================
 *  Unity Project - A Test Framework for C
 *  Copyright (c) 2007 Mike Karlesky, Mark VanderVoord, Greg Williams
 *  [Released under MIT License. Please refer to license.txt for details]
 * ========================================== */

#include "unity_fixture.h"
#include "unity_internals.h"

struct UNITY_FIXTURE_T UnityFixture;

/* If you decide to use the function pointer approach.
 * Build with -D UNITY_OUTPUT_CHAR=outputChar and include <stdio.h>
 * int (*outputChar)(int) = putchar; */

void setUp(void)    { /*does nothing*/ }
void tearDown(void) { /*does nothing*/ }

int UnityMain(const char* namespace, void (*runAllTests)(void), int verbose)
{
    UnityFixture.Verbose = verbose;
    UnityBegin(namespace);
    runAllTests();
    if (!UnityFixture.Verbose) UNITY_PRINT_EOL();
    UnityEnd();
    return (int)Unity.TestFailures;
}

void UnityTestRunner(unityfunction* setup,
                     unityfunction* testBody,
                     unityfunction* teardown,
                     const char* printableName,
                     const char* group,
                     const char* name,
                     const char* file,
                     unsigned int line)
{
    Unity.TestFile = file;
    Unity.CurrentTestName = printableName;
    Unity.CurrentTestLineNumber = line;
    if (UnityFixture.Verbose)
    {
        UnityPrint(printableName);
    #ifndef UNITY_REPEAT_TEST_NAME
        Unity.CurrentTestName = NULL;
    #endif
    }
    else if (UnityFixture.Silent)
    {
        /* Do Nothing */
    }
    else
    {
        UNITY_OUTPUT_CHAR('.');
    }

    Unity.NumberOfTests++;
    UnityPointer_Init();

    UNITY_EXEC_TIME_START();

    if (TEST_PROTECT())
    {
        setup();
        testBody();
    }
    if (TEST_PROTECT())
    {
        teardown();
    }
    if (TEST_PROTECT())
    {
        UnityPointer_UndoAllSets();
    }
    UnityConcludeFixtureTest();
}

void UnityIgnoreTest(const char* printableName, const char* group, const char* name)
{
    Unity.NumberOfTests++;
    Unity.TestIgnores++;
    if (UnityFixture.Verbose)
    {
        UnityPrint(printableName);
        UNITY_PRINT_EOL();
    }
    else if (UnityFixture.Silent)
    {
        /* Do Nothing */
    }
    else
    {
        UNITY_OUTPUT_CHAR('!');
    }
}

/*-------------------------------------------------------- */
/*Automatic pointer restoration functions */
struct PointerPair
{
    void** pointer;
    void* old_value;
};

static struct PointerPair pointer_store[UNITY_MAX_POINTERS];
static int pointer_index = 0;

void UnityPointer_Init(void)
{
    pointer_index = 0;
}

void UnityPointer_Set(void** pointer, void* newValue, UNITY_LINE_TYPE line)
{
    if (pointer_index >= UNITY_MAX_POINTERS)
    {
        UNITY_TEST_FAIL(line, "Too many pointers set");
    }
    else
    {
        pointer_store[pointer_index].pointer = pointer;
        pointer_store[pointer_index].old_value = *pointer;
        *pointer = newValue;
        pointer_index++;
    }
}

void UnityPointer_UndoAllSets(void)
{
    while (pointer_index > 0)
    {
        pointer_index--;
        *(pointer_store[pointer_index].pointer) =
            pointer_store[pointer_index].old_value;
    }
}

void UnityConcludeFixtureTest(void)
{
    if (Unity.CurrentTestIgnored)
    {
        Unity.TestIgnores++;
        UNITY_PRINT_EOL();
    }
    else if (!Unity.CurrentTestFailed)
    {
        if (UnityFixture.Verbose)
        {
            UnityPrint(" ");
            UnityPrint(UnityStrPass);
            UNITY_EXEC_TIME_STOP();
            UNITY_PRINT_EXEC_TIME();
            UNITY_PRINT_EOL();
        }
    }
    else /* Unity.CurrentTestFailed */
    {
        Unity.TestFailures++;
        UNITY_PRINT_EOL();
    }

    Unity.CurrentTestFailed = 0;
    Unity.CurrentTestIgnored = 0;
}
