import json
import os
import re

import neovim
import requests
import time

LC_HOME = '.leetcode-nvim/'
LC_CONFIG = LC_HOME + 'config.json'
LC_SESSION = LC_HOME + 'session.json'
LC_PROBLEMS = LC_HOME + 'problems.json'
LC_PROBLEMS_TMP = LC_HOME + 'problems_tmp.txt'
LC_PROBLEMS_HOME = LC_HOME + 'problems/'
LC_SOLUTIONS_HOME = LC_HOME + 'solutions/'

LC_PROBLEM_ALL = 'all'
LC_PROBLEM_ALGORITHMS = 'algorithms'
LC_PROBLEM_DATABASE = 'database'
LC_PROBLEM_SHELL = 'shell'
LC_PROBLEM_CONCURRENCY = 'concurrency'

LC_PROBLEM_REPR_FULL = 'No. %d %s <%s>'
LC_PROBLEM_REPR_COMPACT = 'no-%d-%s'

REGEXP_LINE = 'No\\. (\\d) .* <([A-Za-z0-9\\-]*)>'
REGEXP_LINE_COMAPCT = 'no-(\\d)-(.+)\\.([a-z]+)'

LC_ENDPOINT_CN = "leetcode.cn"
LC_ENDPOINT_US = "leetcode.com"

URLS = {
    'home': 'https://%s',
    'login': 'https://%s/accounts/login/',
    'problemset': 'https://%s/problemset/all/',
    'problems': 'https://%s/api/problems/%s',
    'progress_all': 'https://%s/api/progress/all/',
    'favorites': 'https://%s/problems/api/favorites/',
    'graphql': 'https://%s/graphql',
    'referer': 'https://%s/problems/%s/',
    'run': 'https://%s/problems/%s/interpret_solution/',
    'run_check': 'https://%s/submissions/detail/%s/check/',
    'latest_submission': 'https://%s/submissions/latest/',
    'submit': 'https://%s/problems/%s/submit/'
}

EXTENSIONS = {
    'cpp': '.cpp',
    'java': '.java',
    'python': '.py',
    'python3': '.py',
    'c': '.c',
    'csharp': '.cs',
    'javascript': '.js',
    'ruby': '.rb',
    'swift': '.swift',
    'golang': '.go',
    'scala': '.scala',
    'kotlin': '.kt',
    'rust': '.rs',
    'php': '.php',
    'typescript': '.ts'
}

COMMENTS = {
    'cpp': '//',
    'java': '//',
    'python': '#',
    'python3': '#',
    'c': '//',
    'csharp': '//',
    'javascript': '//',
    'ruby': '#',
    'swift': '//',
    'golang': '//',
    'scala': '//',
    'kotlin': '//',
    'rust': '//',
    'php': '//',
    'typescript': '//'
}


class LeetcodeSession:

    def __init__(self):
        self._configs = {
            'default_lang': 'c'
        }
        self._endpoint = None
        self._csrftoken = None
        self._leetcode_session = None
        self._init_leetcode_home()
        self._read_session()
        if self.is_logged_in():
            self._api = _LeetcodeApi(self._endpoint, self._csrftoken, self._leetcode_session)

    def _get_path(self, path):
        return self._get_user_home() + path

    def _init_leetcode_home(self):
        leetcode_home = self._get_path(LC_HOME)
        if not os.path.exists(leetcode_home):
            os.mkdir(leetcode_home)
            os.mkdir(self._get_path(LC_PROBLEMS_HOME))
            os.mkdir(self._get_path(LC_SOLUTIONS_HOME))

    def _init_lang_dir(self, lang):
        lang_dir_path = self._get_path(LC_SOLUTIONS_HOME) + lang
        if not os.path.exists(lang_dir_path):
            os.mkdir(lang_dir_path)

    @staticmethod
    def _get_user_home():
        return os.getenv('HOME') + '/'

    @staticmethod
    def _problem_repr_compact(problem_id, title):
        return LC_PROBLEM_REPR_COMPACT % (int(problem_id), title)

    @staticmethod
    def _problem_repr_full(problem_id, title, title_full):
        return LC_PROBLEM_REPR_FULL % (problem_id, title_full, title)

    def set_config(self, key, value):
        self._configs[key] = value

    def get_config(self, key):
        return self._configs.get(key)

    def _read_session(self):
        f = self._get_path(LC_SESSION)
        if os.path.exists(f):
            with open(f, 'r') as inf:
                jo = json.load(inf)
                self._endpoint = jo['endpoint']
                self._csrftoken = jo['csrftoken']
                self._leetcode_session = jo['leetcode_session']

    def is_logged_in(self):
        # todo
        # check login status by launching a request
        return self._endpoint is not None and self._csrftoken is not None and self._leetcode_session is not None

    def login(self, endpoint, csrftoken, leetcode_session):
        f = self._get_path(LC_SESSION)
        with open(f, 'w') as outf:
            jo = {
                'endpoint': endpoint,
                'csrftoken': csrftoken,
                'leetcode_session': leetcode_session
            }
            json.dump(jo, outf)
        self._endpoint = endpoint
        self._csrftoken = csrftoken
        self._leetcode_session = leetcode_session

    def is_premium(self):
        pass

    def get_problems(self, category=LC_PROBLEM_ALL, use_cache=True):
        f = self._get_path(LC_PROBLEMS)
        if use_cache and os.path.exists(f):
            with open(f, 'r') as inf:
                jo = json.load(inf)
        else:
            resp_text = self._api.get_problems(category)
            with open(f, 'w') as outf:
                outf.write(resp_text)
            jo = json.loads(resp_text)

        problems = jo['stat_status_pairs']
        tmpf = self._get_path(LC_PROBLEMS_TMP)
        lines = list(map(lambda x: self._problem_repr_full(x['stat']['frontend_question_id'],
                                                           x['stat']['question__title_slug'].strip(),
                                                           x['stat']['question__title'].strip()),
                         sorted(problems, key=lambda x: x['stat']['frontend_question_id'])))
        with open(tmpf, 'w') as outf:
            outf.write('\n'.join(lines))
        return tmpf, 'All problems loaded!'

    def _get_problem(self, problem_id, title, use_cache=True):
        f = self._get_path(LC_PROBLEMS_HOME) + self._problem_repr_compact(problem_id, title) + '.json'
        if use_cache and os.path.exists(f):
            with open(f, 'r') as inf:
                jo = json.load(inf)
        else:
            resp_text = self._api.get_problem(title)
            with open(f, 'w') as outf:
                outf.write(resp_text)
            jo = json.loads(resp_text)
        return jo

    def get_problem_code(self, problem_id, title, lang, use_cache=True):
        f = self._get_path(LC_SOLUTIONS_HOME) + lang + '/' \
            + self._problem_repr_compact(problem_id, title) \
            + EXTENSIONS[lang]
        if use_cache and os.path.exists(f):
            return f, 'Happy coding! ^_^'
        self._init_lang_dir(lang)
        jo = self._get_problem(problem_id, title)
        lines = jo['data']['question']['content'].split('\n')
        comment = COMMENTS[lang]
        lines.insert(0, '@desc-start')
        lines.append('@desc-end')
        lines = list(map(lambda x: comment + ' ' + x, lines))
        code_data = filter(lambda x: x['langSlug'] == lang, jo['data']['question']['codeSnippets'])
        code_lines = ['', '', comment + ' @code-start'] + list(list(code_data)[0]['code'].split('\n'))
        code_lines.append(comment + ' @code-end')
        with open(f, 'w') as outf:
            outf.write('\n'.join(lines + code_lines))
        return f, 'Happy coding! ^_^'

    @staticmethod
    def _cut_codes(code_lines):
        start_index = LeetcodeSession._find_index(code_lines, '@code-start')
        end_index = LeetcodeSession._find_index(code_lines, '@code-end')
        return code_lines[start_index + 1: end_index]

    @staticmethod
    def _find_index(code_lines, delimiter):
        for i in range(len(code_lines)):
            if delimiter in code_lines[i]:
                return i

    @staticmethod
    def _build_test_code_output(d, testcases):
        run_success = d.get('run_success')
        if run_success is None:
            return json.dumps(d)
        elif run_success:
            correct = d['correct_answer']
            if correct:
                return ('Correct\nInput:\n%s\nExpected Output:\n%s\nOutput:\n%s'
                        % (testcases, d['expected_code_answer'], d['code_answer']))
            else:
                return ('Wrong Answer\nInput:\n%s\nExpected Output:\n%s\nOutput:\n%s'
                        % (testcases, d['expected_code_answer'], d['code_answer'],))
        else:
            return '%s\n%s' % (d['status_msg'], d['full_compile_error'])

    @staticmethod
    def _build_submit_code_output(d):
        run_success = d.get('run_success')
        if run_success is None:
            return 'Request failed, please try again!'
        elif run_success:
            all_pass = d['total_correct'] == d['total_testcases']
            if all_pass:
                return ('Accepted\nTestcases:\n%d/%d\nRuntime Percentile:\n%02.2f\nMemory Percentile:\n%02.2f'
                        % (d['total_correct'], d['total_testcases'], d['runtime_percentile'], d['memory_percentile']))
            else:
                return ('Wrong Answer\nTestcases:\n%d/%d\nInput:\n%s\nExpected Output:\n%s\nOutput:\n%s'
                        % (d['total_correct'], d['total_testcases'], d['input_formatted'], d['expected_output'],
                           d['code_output']))
        else:
            return '%s\n%s' % (d['status_msg'], d['full_compile_error'])

    def test(self, problem_id, title, lang, testcases):
        f = self._get_path(LC_SOLUTIONS_HOME) + lang + '/' \
            + self._problem_repr_compact(problem_id, title) \
            + EXTENSIONS[lang]
        if not testcases:
            jo = self._get_problem(problem_id, title)
            testcases = jo['data']['question']['sampleTestCase']
        with open(f, 'r') as inf:
            code_lines = inf.readlines()
        jo = self._api.test(problem_id, title, lang, code_lines, testcases)
        return self._build_test_code_output(jo, testcases)

    def submit(self, problem_id, title, lang):
        f = self._get_path(LC_SOLUTIONS_HOME) + lang + '/' \
            + self._problem_repr_compact(problem_id, title) \
            + EXTENSIONS[lang]
        with open(f, 'r') as inf:
            code_lines = inf.readlines()
            code_lines = list(map(lambda x: x.rstrip(), code_lines))
        jo = self._api.submit(problem_id, title, lang, self._cut_codes(code_lines))
        return self._build_submit_code_output(jo)

    def get_last_submission(self, problem_id, title, lang):
        f, _ = self.get_problem_code(problem_id, title, lang, True)
        with open(f, 'r') as inf:
            code_lines = inf.readlines()
            code_lines = list(map(lambda x: x.rstrip(), code_lines))
        try:
            jo = self._api.get_last_submission(problem_id, title, lang)
            remote_lines = jo['code'].split('\n')
            start_index = self._find_index(code_lines, '@code-start')
            end_index = self._find_index(code_lines, '@code-end')
            final_lines = code_lines[:start_index + 1] + remote_lines + code_lines[end_index:]
            with open(f, 'w') as outf:
                outf.write('\n'.join(final_lines))
        except RuntimeError:
            return f, 'No code found!'
        else:
            return f, 'Latest submission is retrieved!'


class _LeetcodeApi:

    def __init__(self, endpoint, csrftoken, leetcode_session):
        self._endpoint = endpoint
        self._csrftoken = csrftoken
        self._leetcode_session = leetcode_session

    def _host(self):
        if self._endpoint == 'cn':
            return LC_ENDPOINT_CN
        else:
            return LC_ENDPOINT_US

    def _url(self, name, *varargs):
        return URLS[name] % (self._host(), *varargs)

    @staticmethod
    def check_resp(resp, status_code=200, ex_msg='failed to get expected response'):
        if resp:
            if status_code == resp.status_code:
                return resp
        raise RuntimeError(ex_msg)

    def _build_cookie_string(self):
        return 'csrftoken=' + self._csrftoken + ';' + 'LEETCODE_SESSION=' + self._leetcode_session + ';'

    def _build_headers(self):
        return {
            'Host': 'leetcode.com',
            'Cookie': self._build_cookie_string(),
            'x-csrftoken': self._csrftoken
        }

    @staticmethod
    def _do_get(url, headers, params=None, status_code=200):
        if params is None:
            params = {}
        resp = requests.get(url, headers=headers, params=params)
        return _LeetcodeApi.check_resp(resp, status_code)

    @staticmethod
    def _do_post(url, headers, form_data, status_code=200):
        resp = requests.post(url, headers=headers, json=form_data)
        return _LeetcodeApi.check_resp(resp, status_code)

    def get_progress_all(self):
        url = self._url('progress_all')
        resp = _LeetcodeApi._do_get(url, headers=self._build_headers())
        return resp.text

    def get_problems(self, category):
        url = self._url('problems', category)
        resp = _LeetcodeApi._do_get(url, headers=self._build_headers())
        return resp.text

    def get_problem(self, title):
        url = self._url('graphql')
        resp = self._do_post(url, headers={
            **self._build_headers(),
            'Referer': self._url('referer', title)
        }, form_data={
            'operationName': 'questionData',
            'variables': {
                'titleSlug': title
            },
            'query': '\n'.join([
                'query questionData($titleSlug: String!) {',
                '    question(titleSlug: $titleSlug) {',
                '        title',
                '        titleSlug',
                '        content',
                '        isPaidOnly',
                '        difficulty',
                '        isLiked',
                '        codeSnippets {'
                '            lang',
                '            langSlug',
                '            code',
                '        }',
                '        hints',
                '        status',
                '        sampleTestCase',
                '    }',
                '}'
            ])
        })
        return resp.text

    def _upload_code(self, url_name, run_id_name, title, form_data):
        url = self._url(url_name, title)
        resp = self._do_post(url, headers={
            **self._build_headers(),
            'Referer': self._url('referer', title)
        }, form_data=form_data)
        jo = resp.json()
        run_id = jo[run_id_name]
        url = self._url('run_check', run_id)
        total_rounds = 30  # 30 seconds
        round_index = 0
        final_resp_json = None
        while round_index < total_rounds:
            resp = _LeetcodeApi._do_get(url, headers=self._build_headers())
            resp_json = resp.json()
            if resp_json['state'] == 'SUCCESS':
                final_resp_json = resp.json()
                break
            time.sleep(1)
            round_index += 1
        return final_resp_json

    def test(self, problem_id, title, lang, code_lines, testcases):
        return self._upload_code('run', 'interpret_id', title, form_data={
            'data_input': testcases,
            'judge_type': 'large',
            'lang': lang,
            'question_id': problem_id,
            'typed_code': '\n'.join(code_lines)
        })

    def submit(self, problem_id, title, lang, code_lines):
        return self._upload_code('submit', 'submission_id', title, form_data={
            'lang': lang,
            'question_id': problem_id,
            'typed_code': '\n'.join(code_lines)
        })

    def get_last_submission(self, problem_id, title, lang):
        url = self._url('latest_submission')
        resp = _LeetcodeApi._do_get(url, headers={
            **self._build_headers(),
            'Referer': self._url('referer', title)
        }, params={
            'qid': problem_id,
            'lang': lang
        })
        return resp.json()


@neovim.plugin
class LeetcodePlugin(object):
    def __init__(self, vim):
        self.vim = vim
        lang = self.vim.eval('g:leetcode_default_lang')
        self.session = LeetcodeSession()
        self.session.set_config('default_lang', lang)

    def _echo(self, message):
        self.vim.command('echo "' + message + '"')

    @staticmethod
    def _extract_problem_data(line):
        if re.match(REGEXP_LINE, line):
            p = re.compile(REGEXP_LINE)
        elif re.match(REGEXP_LINE_COMAPCT, line):
            p = re.compile(REGEXP_LINE_COMAPCT)
        else:
            return None, None, None

        tp = p.findall(line)[0]
        if len(tp) == 3:
            return tp
        else:
            return *tp, None

    @staticmethod
    def _extract_problem_data2(line1, line2):
        problem_id, title, ext = LeetcodePlugin._extract_problem_data(line1)
        if not problem_id and not title:
            problem_id, title, ext = LeetcodePlugin._extract_problem_data(line2)
        return problem_id, title, ext

    @staticmethod
    def find_lang_by_extension(extension):
        for k, v in EXTENSIONS.items():
            if v[1:] == extension:
                return k

    @neovim.function('LCLoginWithCookie')
    def lc_login_with_cookie(self, args):
        self.session.login(args[0], args[1], args[2])
        if self.session.is_logged_in():
            self._echo('Successfully logged in with browser cookie!')
        else:
            self._echo("Failed to login, please check your cookie's expiation!")

    @neovim.function('LCListProblems')
    def lc_list_problems(self, args):
        if self.session.is_logged_in():
            category = 'all'
            use_cache = True
            if len(args) == 1:
                category = args[0]
            elif len(args) == 2:
                category = args[0]
                if args[1].lower() == 'true':
                    use_cache = True
                else:
                    use_cache = False
            self._echo('Loading problems...')
            f, msg = self.session.get_problems(category, use_cache)
            self.vim.command('e ' + f)
            self.vim.command('set nomodifiable')
            # self.vim.current.buffer.add_highlight('String', 1, 0, -1, -1)
            self._echo(msg)
        else:
            self._echo('Login with browser cookie first!')

    @neovim.function('LCCoding')
    def lc_coding(self, args):
        if self.session.is_logged_in():
            buf_name = self.vim.current.buffer.name
            buf_name = buf_name.split('/')[-1]
            current_line = self.vim.current.line
            lang = None
            problem_id, title, ext = LeetcodePlugin._extract_problem_data2(current_line, buf_name)
            if ext:
                lang = self.find_lang_by_extension(ext)
            if problem_id and title:
                if len(args) > 0:
                    lang = args[0].lower()
                if not lang:
                    lang = self.session.get_config('default_lang')
                f, msg = self.session.get_problem_code(problem_id, title, lang, True)
                if f:
                    self.vim.command('e ' + f)
                    self.vim.command('set modifiable')
                    self._echo(msg)
                else:
                    self._echo('No code snippet for ' + lang + ' found!')
            else:
                self._echo('No enough information provided!')
        else:
            self._echo('Login with browser cookie first!')

    @neovim.function('LCCodingReset')
    def lc_coding_reset(self, args):
        if self.session.is_logged_in():
            buf_name = self.vim.current.buffer.name
            buf_name = buf_name.split('/')[-1]
            problem_id, title, ext = self._extract_problem_data(buf_name)
            lang = self.find_lang_by_extension(ext)
            if problem_id and title and lang:
                f, msg = self.session.get_problem_code(problem_id, title, lang, False)
                if f:
                    self.vim.command('e ' + f)
                    self.vim.command('set modifiable')
                    self._echo(msg)
            else:
                self._echo('Only the opened solution file can be reset!')

    @neovim.function('LCTest')
    def lc_run(self, args):
        if self.session.is_logged_in():
            buf_name = self.vim.current.buffer.name
            buf_name = buf_name.split('/')[-1]
            if len(args) > 0:
                testcases = args[0]
            else:
                testcases = None
            lang = None
            problem_id, title, ext = self._extract_problem_data(buf_name)
            if ext:
                lang = self.find_lang_by_extension(ext)
            if problem_id and title and lang:
                result_msg = self.session.test(problem_id, title, lang, testcases)
                self._echo(result_msg)
            else:
                self._echo('Not a valid solution file!')
        else:
            self._echo('Login with browser cookie first!')

    @neovim.function('LCSubmit')
    def lc_submit(self, args):
        if self.session.is_logged_in():
            buf_name = self.vim.current.buffer.name.strip()
            buf_name = buf_name.split('/')[-1]
            lang = None
            problem_id, title, ext = self._extract_problem_data(buf_name)
            if ext:
                lang = self.find_lang_by_extension(ext)
            if problem_id and title and lang:
                result_msg = self.session.submit(problem_id, title, lang)
                self._echo(result_msg)
            else:
                self._echo('Not a valid solution file!')
        else:
            self._echo('Login with browser cookie first!')

    @neovim.function("LCGetLatestSubmission")
    def lc_get_latest_submission(self, args):
        if self.session.is_logged_in():
            buf_name = self.vim.current.buffer.name
            buf_name = buf_name.split('/')[-1]
            current_line = self.vim.current.line
            lang = None
            problem_id, title, ext = LeetcodePlugin._extract_problem_data2(buf_name, current_line)
            if ext:
                lang = self.find_lang_by_extension(ext)
            if problem_id and title:
                if len(args) > 0:
                    lang = args[0].lower()
                if not lang:
                    lang = self.session.get_config('default_lang')
                f, msg = self.session.get_last_submission(problem_id, title, lang)
                if f:
                    self.vim.command('e ' + f)
                    self.vim.command('set modifiable')
                    self._echo(msg)
        else:
            self._echo('Login with browser cookie first!')
