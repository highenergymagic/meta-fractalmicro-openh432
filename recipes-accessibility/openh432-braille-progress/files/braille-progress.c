/* SPDX-License-Identifier: MIT */
/* Short-lived progress writer. Never remains alive across BRLTTY handoff. */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/file.h>
#include <unistd.h>

static const unsigned char letters[] = {
	1, 3, 9, 25, 17, 11, 27, 19, 10, 26, 5, 7, 13,
	29, 21, 15, 31, 23, 14, 30, 37, 39, 58, 45, 61, 53
};
static const unsigned char digits[] = {26, 1, 3, 9, 25, 17, 11, 27, 19, 10};

static int frame(const char *label, unsigned int percent, unsigned char out[32])
{
	size_t i, length = strlen(label);

	if (length > 28 || percent > 99)
		return -1;
	memset(out, 0, 32);
	for (i = 0; i < length; i++) {
		if (label[i] == ' ')
			continue;
		if (label[i] < 'a' || label[i] > 'z')
			return -1;
		out[i] = letters[label[i] - 'a'];
	}
	out[29] = 0x3c; /* Number sign; digits occupy cells 31 and 32. */
	out[30] = digits[percent / 10];
	out[31] = digits[percent % 10];
	return 0;
}

static int number(const char *text, unsigned int *result)
{
	char *end;
	unsigned long value;

	if (!*text || strspn(text, "0123456789") != strlen(text))
		return -1;
	errno = 0;
	value = strtoul(text, &end, 10);
	if (errno || *end || value > 99)
		return -1;
	*result = value;
	return 0;
}

int main(int argc, char **argv)
{
	struct { uint32_t mask, closed; } state = {0, 0};
	unsigned char out[32];
	unsigned int value, percent;
	int fd, display, result = 1;
	ssize_t got;

	if (argc != 4 || number(argv[3], &value))
		return 2;
	if (!strcmp(argv[1], "--frame")) {
		if (frame(argv[2], value, out))
			return 2;
		return fwrite(out, 1, sizeof(out), stdout) == sizeof(out) ? 0 : 1;
	}
	if (geteuid() || (strcmp(argv[1], "show") &&
			 strcmp(argv[1], "mark") && strcmp(argv[1], "finish")))
		return 2;
	if (strcmp(argv[1], "show") && value > 8)
		return 2;
	/* Validate labels before touching the boot ledger. */
	if (frame(argv[2], 0, out))
		return 2;
	fd = open("/run/openh432-braille-progress", O_RDWR | O_CREAT |
		  O_CLOEXEC | O_NOFOLLOW, 0600);
	if (fd < 0)
		return 1;
	if (flock(fd, LOCK_EX | LOCK_NB)) {
		int saved_errno = errno;

		close(fd);
		return saved_errno == EWOULDBLOCK ? 0 : 1;
	}
	got = pread(fd, &state, sizeof(state), 0);
	if (got != 0 && got != (ssize_t)sizeof(state))
		goto done;
	if (state.closed) {
		result = 0;
		goto done;
	}
	percent = value;
	if (strcmp(argv[1], "show")) {
		state.mask |= 1U << value;
		percent = (unsigned int)__builtin_popcount(state.mask & 0x1ff) * 100 / 9;
		if (!strcmp(argv[1], "finish")) {
			state.closed = 1;
			percent = 99;
		}
		if (pwrite(fd, &state, sizeof(state), 0) != (ssize_t)sizeof(state))
			goto done;
	}
	if (percent > 99)
		percent = 99;
	if (frame(argv[2], percent, out))
		goto done;
	display = open("/dev/h432b-braille", O_WRONLY | O_CLOEXEC | O_NOFOLLOW);
	if (display < 0)
		goto done;
	result = write(display, out, sizeof(out)) == (ssize_t)sizeof(out) ? 0 : 1;
	close(display);
done:
	close(fd);
	return result;
}
