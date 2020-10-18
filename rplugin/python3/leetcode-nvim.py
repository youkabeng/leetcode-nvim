import json
import os
import re

import neovim
import requests

LC_HOME = '.leetcode-nvim/'
LC_CONFIG = LC_HOME + 'config.json'
LC_SESSION = LC_HOME + 'session.json'
LC_PROBLEMS = LC_HOME + 'problems.json'
LC_PROBLEMS_HOME = LC_HOME + 'problems/'
LC_SOLUTIONS_HOME = LC_HOME + 'solutions/'

LC_PROBLEM_ALL = 'all'
LC_PROBLEM_ALGORITHMS = 'algorithms'
LC_PROBLEM_DATABASE = 'database'
LC_PROBLEM_SHELL = 'shell'
LC_PROBLEM_CONCURRENCY = 'concurrency'

LC_PROBLEM_REPR_FULL = 'No. %d %s <%s>'
LC_PROBLEM_REPR_COMPACT = 'no-%d-%s'

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
    'submit': ''
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

default_lang = 'c'
default_problem_id = 1


def init_leetcode_home():
    leetcode_home = get_path(LC_HOME)
    if not os.path.exists(leetcode_home):
        os.mkdir(leetcode_home)
        # create config.json
        with open(get_path(LC_CONFIG), 'w') as outf:
            d = {'default_lang': default_lang}
            json.dump(d, outf)
        # create problems dir
        os.mkdir(get_path(LC_PROBLEMS_HOME))
        # create solutions dir
        os.mkdir(get_path(LC_SOLUTIONS_HOME))


def init_lang_dir(lang):
    lang_dir_path = get_path(LC_SOLUTIONS_HOME) + lang
    if not os.path.exists(lang_dir_path):
        os.mkdir(lang_dir_path)


def get_user_home():
    return os.getenv('HOME') + '/'


def get_path(path):
    return get_user_home() + path


def problem_repr_compact(problem_id, title):
    return LC_PROBLEM_REPR_COMPACT % (int(problem_id), title)


def problem_repr_full(problem_id, title, title_full):
    return LC_PROBLEM_REPR_FULL % (problem_id, title_full, title)


def find_lang_by_extension(extension):
    for k, v in EXTENSIONS.items():
        if v[1:] == extension:
            return k


def extract_problem_id_and_title(line):
    p = re.compile('No\\. (\\d) .* <([A-Za-z0-9\\-]*)>')
    return p.findall(line)[0]


class LeetCodeSession:
    _SESSION_FILE = get_path(LC_SESSION)

    def __init__(self):
        init_leetcode_home()
        self._endpoint = None
        self._csrftoken = None
        self._leetcode_session = None
        self._read_session()
        if self.is_logged_in():
            self._api = _LeetCodeApi(self._endpoint, self._csrftoken, self._leetcode_session)

    def _read_session(self):
        if os.path.exists(LeetCodeSession._SESSION_FILE):
            with open(LeetCodeSession._SESSION_FILE, 'r') as inf:
                d = json.load(inf)
                self._endpoint = d['endpoint']
                self._csrftoken = d['csrftoken']
                self._leetcode_session = d['leetcode_session']

    def is_logged_in(self):
        # todo
        # check login status by launching a request
        return self._endpoint is not None and self._csrftoken is not None and self._leetcode_session is not None

    def login(self, endpoint, csrftoken, leetcode_session):
        f = get_path(LC_SESSION)
        with open(f, 'w') as outf:
            d = {
                'endpoint': endpoint,
                'csrftoken': csrftoken,
                'leetcode_session': leetcode_session
            }
            json.dump(d, outf)
        self._endpoint = endpoint
        self._csrftoken = csrftoken
        self._leetcode_session = leetcode_session

    def is_premium(self):
        pass

    def get_problems(self, category=LC_PROBLEM_ALL, use_cache=True):
        f = get_path(LC_PROBLEMS)
        if use_cache and os.path.exists(f):
            with open(f, 'r') as inf:
                jo = json.load(inf)
        else:
            resp_text = self._api.get_problems(category)
            with open(f, 'w') as outf:
                outf.write(resp_text)
            jo = json.loads(resp_text)

        problems = jo['stat_status_pairs']
        return list(
            map(lambda x: problem_repr_full(x['stat']['frontend_question_id'],
                                            x['stat']['question__title_slug'].strip(),
                                            x['stat']['question__title'].strip()),
                sorted(problems, key=lambda x: x['stat']['frontend_question_id'])))

    def _get_problem(self, problem_id, title, use_cache=True):
        f = get_path(LC_PROBLEMS_HOME) + problem_repr_compact(problem_id, title) + '.json'
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
        f = get_path(LC_SOLUTIONS_HOME) + lang + '/' \
            + problem_repr_compact(problem_id, title) \
            + EXTENSIONS[lang]
        if use_cache and os.path.exists(f):
            return f
        init_lang_dir(lang)
        d = self._get_problem(problem_id, title)
        lines = d['data']['question']['content'].split('\n')
        comment = COMMENTS[lang]
        lines.insert(0, '@desc-start')
        lines.append('@desc-end')
        lines = list(map(lambda x: comment + ' ' + x, lines))
        code_data = filter(lambda x: x['langSlug'] == lang, d['data']['question']['codeSnippets'])
        code_lines = ['', '', comment + ' @code-start'] + list(list(code_data)[0]['code'].split('\n'))
        code_lines.append(comment + ' @code-end')
        with open(f, 'w') as outf:
            outf.write('\n'.join(lines + code_lines))
        return f

    def _cut_codes(self, code_lines):
        return code_lines[code_lines.index('@code-start') + 1: code_lines.index('@code-end')]

    def test(self, code_file_name, testcases):
        lang = find_lang_by_extension('.', code_file_name.split('.')[1])
        problem_id, title = extract_problem_id_and_title(code_file_name)
        f = get_path(LC_SOLUTIONS_HOME) + lang + code_file_name
        if not testcases:
            d = self._get_problem(problem_id, title)
            testcases = d['data']['question']['sampleTestCase']
        with open(f, 'r') as inf:
            code_lines = inf.readlines().split('\n')
        d = self._api.test(problem_id, title, lang, self._cut_codes(code_lines), testcases)

    def submit(self, code_file_name):
        pass


class _LeetCodeApi:

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

    def _do_get(self, url, headers, status_code=200):
        resp = requests.get(url, headers=headers)
        return _LeetCodeApi.check_resp(resp, status_code)

    def _do_post(self, url, headers, form_data, status_code=200):
        resp = requests.post(url, headers=headers, json=form_data)
        return _LeetCodeApi.check_resp(resp, status_code)

    def get_progress_all(self):
        url = self._url('progress_all')
        resp = self._do_get(url, headers=self._build_headers())
        return resp.text

    def get_problems(self, category):
        url = self._url('problems', category)
        resp = self._do_get(url, headers=self._build_headers())
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

    def test(self, question_id, title, lang, code_lines, testcases):
        url = self._url('run', title)
        resp = self._do_post(url, headers={
            **self._build_headers(),
            'Referer': self._url('referer', title)
        }, form_data={
            'data_input': testcases,
            'judge_type': 'large',
            'lang': lang,
            'question_id': question_id,
            'typed_code': '\n'.join(self._cut_codes(code_lines))
        })
        d = resp.json()
        interpret_id = d['interpret_id']
        url = urls['run_check'] % interpret_id
        total_rounds = 30  # 30 seconds
        round_index = 0
        final_resp_json = None
        while round_index < total_rounds:
            resp = do_get(url, headers=build_headers())
            resp_json = resp.json()
            if resp_json['state'] != 'PENDING':
                final_resp_json = resp.json()
                break
            time.sleep(1)
            round_index += 1
        return final_resp_json


@neovim.plugin
class LeetcodePlugin(object):
    def __init__(self, vim):
        self.vim = vim
        self.session = LeetCodeSession()

    def _echo(self, message):
        self.vim.command('echo "' + message + '"')

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
            lines = self.session.get_problems(category, use_cache)

            buf = self.vim.current.buffer
            if buf.name.strip() != '' or ''.join(buf[:]).strip() != '':
                self.vim.command('new')
            self.vim.current.buffer[:] = lines
            self.vim.command('set nomodifiable')
            # self.vim.current.buffer.add_highlight('String', 1, 0, -1, -1)
            self._echo('All problems loaded!')
        else:
            self._echo('Login with browser cookie first!')

    @neovim.function('LCCoding')
    def lc_coding(self, args):
        if self.session.is_logged_in():
            lang = default_lang
            use_cache = True
            if len(args) == 1:
                lang = args[0].lower()
            elif len(args) == 2:
                lang = args[0].lower()
                use_cache = args[1].lower() == 'true'
            current_line = self.vim.current.line
            if current_line:
                problem_id, title = extract_problem_id_and_title(current_line)
                f = self.session.get_problem_code(problem_id, title, lang, use_cache)
                if f:
                    self.vim.command('e ' + f)
                    self.vim.command('set modifiable')
                    # self.vim.current.buffer.append('// @code-start', 0)
                    self._echo('Happy coding! ^_^')
                else:
                    self._echo('No code snippet for ' + lang + ' found!')
            else:
                self._echo('You should get problem list first and select one!')
        else:
            self._echo('Login with browser cookie first!')

    @neovim.function('LCTest')
    def lc_run(self, args):
        buf_name = self.vim.current.buffer.name.strip()
        code_lines = self.vim.current.buffer[:]
        if buf_name:
            buf_name = buf_name.split('/')[-1]
            qid = buf_name.split('-')[1]
            title_slug = re.sub('^no-\\d+-', '', buf_name.split('/')[-1].split('.')[0])
            _, ext = buf_name.split('.')
            lang = find_lang_by_extension(ext)
            if title_slug and lang:
                d = self.session.run(qid, title_slug, lang, code_lines)
                if d['run_success']:
                    self._echo('Congrats!')
                else:
                    self._echo(d['status_msg'] + '\n' + d['full_compile_error'])
            else:
                self._echo('Not a valid solution leetcodenvim code file.')
        else:
            self._echo('Not a valid solution leetcodenvim code file.')

# session = LeetCodeSession()
# d = session.get_problem_code(1, 'two-sum', 'c')
# print(d)
