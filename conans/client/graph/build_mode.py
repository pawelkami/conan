import fnmatch

from conans.client.output import ScopedOutput
from conans.errors import ConanException


class BuildMode(object):
    """ build_mode => ["*"] if user wrote "--build"
                   => ["hello*", "bye*"] if user wrote "--build hello --build bye"
                   => False if user wrote "never"
                   => True if user wrote "missing"
                   => "outdated" if user wrote "--build outdated"
    """
    def __init__(self, params, output):
        self._out = output
        self.outdated = False
        self.missing = False
        self.never = False
        self.patterns = []
        self._unused_patterns = []
        self.all = False
        if params is None:
            return

        assert isinstance(params, list)
        if len(params) == 0:
            self.all = True
        else:
            for param in params:
                if param == "outdated":
                    self.outdated = True
                elif param == "missing":
                    self.missing = True
                elif param == "never":
                    self.never = True
                else:
                    self.patterns.append("%s" % param)

            if self.never and (self.outdated or self.missing or self.patterns):
                raise ConanException("--build=never not compatible with other options")
        self._unused_patterns = list(self.patterns)

    def forced(self, conan_file, reference):
        if self.never:
            return False
        if self.all:
            return True

        if conan_file.build_policy_always:
            out = ScopedOutput(str(reference), self._out)
            out.info("Building package from source as defined by build_policy='always'")
            return True

        ref = reference.name
        # Patterns to match, if package matches pattern, build is forced
        force_build = any([fnmatch.fnmatch(ref, pattern) for pattern in self.patterns])
        return force_build

    def allowed(self, conan_file, reference):
        return (self.missing or self.outdated or self.forced(conan_file, reference) or
                conan_file.build_policy_missing)

    def check_matches(self, references):
        for pattern in list(self._unused_patterns):
            matched = any(fnmatch.fnmatch(ref, pattern) for ref in references)
            if matched:
                self._unused_patterns.remove(pattern)

    def report_matches(self):
        for pattern in self._unused_patterns:
            self._out.error("No package matching '%s' pattern" % pattern)