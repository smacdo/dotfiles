// Author: Scott MacDonald.
// Purpose: CLI program that locks a MacOS desktop session when executed.
//
// This program uses the undocumented private framework called "Login" to
// achieve this effect. For more details, see:
//   https://stackoverflow.com/q/1976520
#include <stdlib.h>
#include <stdio.h>
#include <string.h>

const int VERSION = 1;

extern void SACLockScreenImmediate(); // Private function from Login framework.

/** Print help text for the user to standard out. */
void help() {
  printf("Lock the current desktop session\n");
  printf("Options: \n");
  printf(" --help    -h   Show help text.\n");
  printf(" --version -v   Show program version.\n");
}

/** Print current version to standard out. */
void version() {
  printf("Version %d\n", VERSION);
}

/**
 * Parse the command line, and process any relevant arguments passed to the
 * program.
 *
 * @param  outExitCode  Will be set to an exit code if function returns false.
 * @return True if the program should continue execution, false otherwise.
 */
int checkArgs(int argc, char* argv[], int* outExitCode) {
  int isOk = 1;
  int exitCode = 0;

  for (int i = 1; i < argc; ++i) {
    isOk = 0; // any argument will make the program exit early.

    if (strcmp(argv[i], "-h") == 0 || strcmp(argv[i], "--help") == 0) {
      help();
    } else if (strcmp(argv[i], "-v") == 0 || strcmp(argv[i], "--version") == 0) {
      version();
    } else {
      fprintf(stderr, "Unknown option argument: %s\n", argv[i]);
      fprintf(stderr, "Get help by typing \"%s -h\"\n", argv[0]);

      exitCode = EXIT_FAILURE;
    }
  }

  if (!isOk && outExitCode != NULL) {
    *outExitCode = exitCode;
  }

  return isOk;
}

/** Application entry point. **/
int main(int argc, char* argv[]) {
  // Show help if requested, otherwise lock the computer unless there are
  // unrecogonized arguments.
  int exitCode = EXIT_SUCCESS;
  
  if (checkArgs(argc, argv, &exitCode) == 1) {
    SACLockScreenImmediate();
  }

  return exitCode;
}
