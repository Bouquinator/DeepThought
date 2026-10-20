#include "get_next_line_bonus.h"

static char	*take_line(char **stash)
{
	char	*nl = gnl_strchr(*stash, '\n');
	size_t	len = nl ? (size_t)(nl - *stash) + 1 : gnl_strlen(*stash);
	char	*line = gnl_join(NULL, *stash, len);
	char	*rest;

	if (!line)
		return (free(*stash), *stash = NULL, NULL);
	rest = NULL;
	if ((*stash)[len])
	{
		rest = gnl_join(NULL, *stash + len, gnl_strlen(*stash + len));
		if (!rest)
			return (free(line), free(*stash), *stash = NULL, NULL);
	}
	free(*stash);
	*stash = rest;
	return (line);
}

char	*get_next_line(int fd)
{
	static char	*stashes[1024];
	char		*buf;
	ssize_t		n;

	if (fd < 0 || fd >= 1024 || BUFFER_SIZE <= 0)
		return (NULL);
	buf = malloc((size_t)BUFFER_SIZE + 1);
	if (!buf)
		return (free(stashes[fd]), stashes[fd] = NULL, NULL);
	n = 1;
	while (!gnl_strchr(stashes[fd], '\n') && n > 0)
	{
		n = read(fd, buf, BUFFER_SIZE);
		if (n < 0)
			return (free(buf), free(stashes[fd]), stashes[fd] = NULL, NULL);
		if (n > 0)
		{
			stashes[fd] = gnl_join(stashes[fd], buf, (size_t)n);
			if (!stashes[fd])
				return (free(buf), NULL);
		}
	}
	free(buf);
	if (!stashes[fd] || !*stashes[fd])
		return (free(stashes[fd]), stashes[fd] = NULL, NULL);
	return (take_line(&stashes[fd]));
}
