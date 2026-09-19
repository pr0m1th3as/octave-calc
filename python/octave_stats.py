# Copyright (C) 2026 Andreas Bertsatos <abertsatos@biol.uoa.gr>
#
# This file is part of the octave-calc extension.
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see <https://www.gnu.org/licenses/>.

"""The analyses under Data > Statistics with GNU Octave, and nothing about
LibreOffice.

Each analysis is an Octave function in the extension's octave folder, which
runs the statistics package and returns its results laid out as the cells a
Calc user sees.  Here the input range is checked cell by cell, so that a
refusal names the cell, and turned into that function's arguments.  The
analysis itself, grouping included, is the Octave function's.
"""

import octave_core

# The Octave package every analysis loads in its sandbox.
PACKAGE = 'statistics'

# How the input range holds the groups: one per column or one per row, each
# may be headed by its name, or two columns, each value beside the label of
# its group, in either order.
BY = ('columns', 'rows', 'labels-data', 'data-labels')

# What an analysis does with the cells it reads: 'range', two or more
# independent groups in one of the four layouts; 'matched', one measurement
# per column, or per row, taken on the same subjects, so that a row of the
# range is one subject; 'factors', each value beside the two factors it was
# measured under; or 'none', it reads no cells at all.
INPUTS = ('range', 'matched', 'factors', 'none')

# What a column or a row of the input range holds, by the kind of input.  The
# dialog and every refusal say it in the user's words, since reading matched
# measurements as independent groups, or the other way about, answers a
# question the user did not ask and says nothing about it.
NOUN = {'range': 'group', 'matched': 'measurement', 'factors': 'factor'}


def allowed (by, kind = 'range'):
  """What the input range may hold, read BY that layout for an analysis of
  that KIND, ending a refusal."""
  noun = NOUN.get (kind, NOUN['range'])
  if (by == 'columns'):
    return ('the input range may hold %s names in its first row, then '
            'numbers and empty cells only.' % noun)
  if (by == 'rows'):
    return ('the input range may hold %s names in its first column, then '
            'numbers and empty cells only.' % noun)
  return ('the values may be numbers or empty cells, and the %s labels text '
          'or numbers.' % noun)

# The categories, in the order the dialog lists them, each with the sentence
# shown under the category.
CATEGORIES = {
  'Group comparisons':
    'Tests whether two or more groups differ, and which of them do.',
  'Association tests':
    'Measures whether two variables move together, and tests independence.',
  'Regression models':
    'Fits a model that predicts one variable from others.',
  'Multivariate analyses':
    'Finds the structure in many variables at once.',
  'Distribution fitting':
    'Fits a distribution to a sample, and tests whether it fits.',
  'Random numbers':
    'Draws a sample from a distribution and the parameters you give it.',
  'Experimental design':
    'Plans a study before the data exist: how many observations are needed, '
    'and which combinations to run.'}


def category_names ():
  """The categories in the order the dialog lists them."""
  return tuple (CATEGORIES)

# The options the three power analyses share, in the order their functions
# take them.  The null standard deviation is taken by the z and t tests and
# ignored by the rest, since the dialog cannot leave a number blank.
POWER_TEST = {'name': 'testtype', 'kind': 'choice', 'label': 'Test:',
              'hint': 'Which test the study will use.',
              'choices': (('t', 'One-sample or paired t-test'),
                          ('t2', 'Two-sample t-test'),
                          ('z', 'One-sample z-test'),
                          ('var', 'Chi-square test of a variance'),
                          ('p', 'Test of a proportion'),
                          ('r', 'Test of a correlation')),
              'default': 't'}

NULL_VALUE = {'name': 'nullvalue', 'kind': 'number', 'label': 'Null value:',
              'hint': 'The mean, proportion, variance or correlation under '
                      'the null hypothesis.',
              'accepts': 'a number', 'minimum': float ('-inf'),
              'maximum': float ('inf'), 'default': '5'}

NULL_SD = {'name': 'nullsd', 'kind': 'number',
           'label': 'Null standard deviation:',
           'hint': 'Taken by the t and z tests; ignored by the others.',
           'accepts': 'a number greater than 0', 'minimum': 0.0,
           'maximum': float ('inf'), 'default': '2'}

SAMPLE_SIZE = {'name': 'n', 'kind': 'number', 'label': 'Sample size:',
               'hint': 'Observations in the study, or in each group.',
               'accepts': 'a whole number of 2 or more', 'minimum': 1.0,
               'maximum': float ('inf'), 'whole': True, 'default': '30'}

ALPHA_LEVEL = {'name': 'alpha', 'kind': 'number',
               'label': 'Significance level:',
               'hint': 'The chance of a false positive. 0.05 by default.',
               'accepts': 'a number greater than 0 and less than 1',
               'minimum': 0.0, 'maximum': 1.0, 'default': '0.05'}

# The layouts an analysis of two factors takes: the two factor columns
# before the values, or after them.  A column or a row per level cannot say
# which level of the other factor a value belongs to, so neither is offered.
FACTORS = ('labels-data', 'data-labels')


# The layouts an analysis of matched measurements takes: one per column, or
# one per row.  Values beside their labels cannot say which subject a value
# belongs to, so they are not offered.
MATCHED = ('columns', 'rows')

# The options the matched analyses share, in the order their functions take
# them.  The first measurement is always the one the alternative is about.
TAIL_MEANS = {'name': 'tail', 'kind': 'choice', 'label': 'Alternative:',
              'hint': 'What the test is prepared to find, the first '
                      'measurement against the second.',
              'choices': (('both', 'the means differ'),
                          ('right', 'the first mean is greater'),
                          ('left', 'the first mean is smaller')),
              'default': 'both'}

TAIL_MEDIANS = {'name': 'tail', 'kind': 'choice', 'label': 'Alternative:',
                'hint': 'What the test is prepared to find, the first '
                        'measurement against the second.',
                'choices': (('both', 'the medians differ'),
                            ('right', 'the first median is greater'),
                            ('left', 'the first median is smaller')),
                'default': 'both'}

METHOD_EXACT = {'name': 'method', 'kind': 'choice', 'label': 'p-value:',
                'hint': 'Exact enumeration, or the normal approximation. '
                        'Chosen by the sample size unless set.',
                'choices': (('auto', 'chosen by the sample size'),
                            ('exact', 'exact'),
                            ('approximate', 'approximate')),
                'default': 'auto'}

# Every analysis, by the command that runs it, in the order its category lists
# them.  Adding one is this entry plus its Octave function, and nothing else:
#
#   category  which list it appears under
#   title     the dialog's title and the first cell of the results
#   function  the Octave function in the octave folder
#   detail    what it does and when to use it, shown under the list
#   input     'range', the analysis reads the cells of an input range, or
#             'none', it takes its options alone and reads no cells
#   layouts   the ways it takes its input range, from BY, or () when it reads
#             no cells
#   options   what the user chooses besides the ranges, passed to the function
#             after the range, the layout and the names, in declared order.
#             Each carries 'name', 'label', 'hint', 'default' and a 'kind':
#             'choice' holds 'choices', ((value, label), ...), and reaches the
#             function as text; 'number' holds 'minimum', 'maximum' and
#             'accepts', the refusal's words, and reaches it as a number,
#             whole when it holds 'whole'; 'numbers' holds the same and
#             reaches the function as a range of one row
ANALYSES = {
  'KruskalWallis': {
    'category': 'Group comparisons',
    'input': 'range',
    'title': 'Kruskal-Wallis Test',
    'function': 'octave_calc_kruskalwallis',
    'detail': 'Compares three or more independent groups by rank, without '
              'assuming the values are normally distributed.\n\n'
              'Use it when the groups are independent, the values are at '
              'least ordinal, and the data are skewed, heavy tailed, or too '
              'few to judge. It answers whether any group differs; the '
              'pairwise comparisons say which.\n\n'
              'For two groups use the Mann-Whitney U test. For normally '
              'distributed values, one-way ANOVA is more powerful.',
    'layouts': BY,
    'options': (
      {'name': 'ctype', 'kind': 'choice', 'label': 'Comparisons:',
       'hint': 'How the p-values of the pairwise comparisons are adjusted.',
       'choices': (('holm', 'Holm'), ('bonferroni', 'Bonferroni'),
                   ('scheffe', 'Scheffe'), ('mvt', 'Multivariate t'),
                   ('hochberg', 'Hochberg'), ('fdr', 'False discovery rate'),
                   ('lsd', 'None')),
       'default': 'holm'},
      {'name': 'alpha', 'kind': 'number', 'label': 'Significance level:',
       'hint': 'Sets the confidence intervals. 0.05 by default.',
       'accepts': 'a number greater than 0 and less than 1',
       'minimum': 0.0, 'maximum': 1.0, 'default': '0.05'})},
  'Anova1': {
    'category': 'Group comparisons',
    'input': 'range',
    'title': 'One-way ANOVA',
    'function': 'octave_calc_anova1',
    'detail': 'Compares the means of two or more independent groups, by '
              'weighing the spread between the groups against the spread '
              'within them.\n\n'
              'Use it when the groups are independent, the values are '
              'measured on a scale, and each group is roughly normal. It '
              'answers whether any mean differs; the pairwise comparisons '
              'say which.\n\n'
              'When the groups have unequal variances, choose Welch. When '
              'the data are skewed or few, the Kruskal-Wallis Test is '
              'safer.',
    'layouts': BY,
    'options': (
      {'name': 'ctype', 'kind': 'choice', 'label': 'Comparisons:',
       'hint': 'How the p-values of the pairwise comparisons are adjusted.',
       'choices': (('holm', 'Holm'), ('bonferroni', 'Bonferroni'),
                   ('scheffe', 'Scheffe'), ('mvt', 'Multivariate t'),
                   ('hochberg', 'Hochberg'), ('fdr', 'False discovery rate'),
                   ('lsd', 'None')),
       'default': 'holm'},
      {'name': 'alpha', 'kind': 'number', 'label': 'Significance level:',
       'hint': 'Sets the confidence intervals. 0.05 by default.',
       'accepts': 'a number greater than 0 and less than 1',
       'minimum': 0.0, 'maximum': 1.0, 'default': '0.05'},
      {'name': 'vartype', 'kind': 'choice', 'label': 'Variances:',
       'hint': 'Welch does not assume the groups share a variance.',
       'choices': (('equal', 'equal (assumed)'),
                   ('unequal', 'non-equal (Welch)')),
       'default': 'equal'})},
  'Ttest2': {
    'category': 'Group comparisons',
    'input': 'range',
    'title': 'Two-sample t-test',
    'function': 'octave_calc_ttest2',
    'detail': 'Compares the means of two independent groups, weighing the '
              'difference between them against the spread within them.\n\n'
              'Use it when the two groups are independent, the values are '
              'measured on a scale, and each group is roughly normal. It '
              'answers whether the means differ, and by how much, with a '
              'confidence interval for the difference.\n\n'
              'When the groups have unequal variances, choose Welch. When '
              'the data are skewed or few, the Mann-Whitney U test is '
              'safer. For three or more groups use one-way ANOVA, and for '
              'two measurements of the same subjects the paired t-test.',
    'layouts': BY,
    'options': (
      {'name': 'vartype', 'kind': 'choice', 'label': 'Variances:',
       'hint': 'Welch does not assume the groups share a variance.',
       'choices': (('equal', 'equal (assumed)'),
                   ('unequal', 'non-equal (Welch)')),
       'default': 'equal'},
      {'name': 'tail', 'kind': 'choice', 'label': 'Alternative:',
       'hint': 'What the test is prepared to find, the first group against '
               'the second.',
       'choices': (('both', 'the means differ'),
                   ('right', 'the first mean is greater'),
                   ('left', 'the first mean is smaller')),
       'default': 'both'},
      {'name': 'alpha', 'kind': 'number', 'label': 'Significance level:',
       'hint': 'Sets the confidence interval. 0.05 by default.',
       'accepts': 'a number greater than 0 and less than 1',
       'minimum': 0.0, 'maximum': 1.0, 'default': '0.05'})},
  'Ranksum': {
    'category': 'Group comparisons',
    'input': 'range',
    'title': 'Mann-Whitney U test',
    'function': 'octave_calc_ranksum',
    'detail': 'Compares two independent groups by rank, without assuming '
              'the values are normally distributed.\n\n'
              'Use it when the two groups are independent, the values are '
              'at least ordinal, and the data are skewed, heavy tailed, or '
              'too few to judge. It answers whether one group tends to hold '
              'the larger values.\n\n'
              'For normally distributed values the two-sample t-test is '
              'more powerful. For three or more groups use the '
              'Kruskal-Wallis Test, and for two measurements of the same '
              'subjects the Wilcoxon signed-rank test.',
    'layouts': BY,
    'options': (
      {'name': 'method', 'kind': 'choice', 'label': 'p-value:',
       'hint': 'Exact enumeration, or the normal approximation. Chosen by '
               'the sample sizes unless set.',
       'choices': (('auto', 'chosen by the sample sizes'),
                   ('exact', 'exact'), ('approximate', 'approximate')),
       'default': 'auto'},
      {'name': 'tail', 'kind': 'choice', 'label': 'Alternative:',
       'hint': 'What the test is prepared to find, the first group against '
               'the second.',
       'choices': (('both', 'the medians differ'),
                   ('right', 'the first median is greater'),
                   ('left', 'the first median is smaller')),
       'default': 'both'},
      {'name': 'alpha', 'kind': 'number', 'label': 'Significance level:',
       'hint': 'The chance of a false positive. 0.05 by default.',
       'accepts': 'a number greater than 0 and less than 1',
       'minimum': 0.0, 'maximum': 1.0, 'default': '0.05'})},
  'VarTestN': {
    'category': 'Group comparisons',
    'input': 'range',
    'title': 'Equal variances',
    'function': 'octave_calc_vartestn',
    'detail': 'Tests whether two or more groups are equally spread, which '
              'the t-tests and ANOVA assume.\n\n'
              'Use it to check that assumption before trusting one of '
              'those, or when the spread is itself the question: two '
              'machines may fill to the same average weight and differ in '
              'how consistently they do it. Two groups also get the ratio '
              'of their variances with a confidence interval.\n\n'
              "Bartlett's test is the most powerful when every group is "
              'normal, and the most easily misled when one is not. The '
              'Levene and Brown-Forsythe tests weigh each value against its '
              "group's mean or median instead, and hold up under skew and "
              'outliers.',
    'layouts': BY,
    'options': (
      {'name': 'testtype', 'kind': 'choice', 'label': 'Test:',
       'hint': 'Bartlett assumes each group is normal; the rest do not.',
       'choices': (('Bartlett', 'Bartlett'),
                   ('LeveneQuadratic', 'Levene, squared deviations'),
                   ('LeveneAbsolute', 'Levene, absolute deviations'),
                   ('BrownForsythe', 'Brown-Forsythe'),
                   ('OBrien', "O'Brien")),
       'default': 'Bartlett'},
      {'name': 'alpha', 'kind': 'number', 'label': 'Significance level:',
       'hint': 'Sets the confidence interval of the ratio. 0.05 by default.',
       'accepts': 'a number greater than 0 and less than 1',
       'minimum': 0.0, 'maximum': 1.0, 'default': '0.05'})},
  'Anova2': {
    'category': 'Group comparisons',
    'input': 'factors',
    'title': 'Two-way ANOVA',
    'function': 'octave_calc_anova2',
    'detail': 'Compares the means of groups formed by two factors at once, '
              'and asks whether the effect of one depends on the level of '
              'the other.\n\n'
              'Use it when every value was measured under one level of each '
              'factor: a yield under a fertiliser and a variety, a score '
              'under a treatment and an age band. It answers three '
              'questions, one for each factor and one for their interaction, '
              'and the comparisons say which levels differ.\n\n'
              'The interaction needs a combination measured more than once. '
              'With one value per combination, take the two effects as '
              'adding. For one factor use one-way ANOVA.',
    'layouts': FACTORS,
    'options': (
      {'name': 'model', 'kind': 'choice', 'label': 'Model:',
       'hint': 'Whether the effect of one factor may depend on the level of '
               'the other.',
       'choices': (('interaction', 'the two effects and their interaction'),
                   ('linear', 'the two effects, taken to add')),
       'default': 'interaction'},
      {'name': 'ctype', 'kind': 'choice', 'label': 'Comparisons:',
       'hint': 'How the p-values of the pairwise comparisons are adjusted.',
       'choices': (('holm', 'Holm'), ('bonferroni', 'Bonferroni'),
                   ('scheffe', 'Scheffe'), ('mvt', 'Multivariate t'),
                   ('hochberg', 'Hochberg'), ('fdr', 'False discovery rate'),
                   ('lsd', 'None')),
       'default': 'holm'},
      ALPHA_LEVEL)},
  'TtestPaired': {
    'category': 'Group comparisons',
    'input': 'matched',
    'title': 'Paired t-test',
    'function': 'octave_calc_ttestpaired',
    'detail': 'Compares two measurements taken on the same subjects, by '
              'testing whether their differences average to zero.\n\n'
              'Use it when each row is one subject measured twice, before '
              'and after, left and right, two methods on the same samples. '
              'Pairing removes the differences between subjects, so it finds '
              'a smaller effect than the two-sample test on the same '
              'numbers.\n\n'
              'For independent groups use the two-sample t-test. When the '
              'differences are skewed or few, the Wilcoxon signed-rank test '
              'is safer. For three or more measurements use the Friedman '
              'test.',
    'layouts': MATCHED,
    'options': (TAIL_MEANS, ALPHA_LEVEL)},
  'SignRank': {
    'category': 'Group comparisons',
    'input': 'matched',
    'title': 'Wilcoxon signed-rank test',
    'function': 'octave_calc_signrank',
    'detail': 'Compares two measurements taken on the same subjects by the '
              'rank of their differences, without assuming those differences '
              'are normally distributed.\n\n'
              'Use it when each row is one subject measured twice and the '
              'differences are skewed, heavy tailed, or too few to judge. It '
              'weighs how large each difference is as well as its '
              'direction.\n\n'
              'For normally distributed differences the paired t-test is '
              'more powerful. Where only the direction of a difference can '
              'be trusted, the sign test asks less of the data.',
    'layouts': MATCHED,
    'options': (METHOD_EXACT, TAIL_MEDIANS, ALPHA_LEVEL)},
  'SignTest': {
    'category': 'Group comparisons',
    'input': 'matched',
    'title': 'Sign test',
    'function': 'octave_calc_signtest',
    'detail': 'Compares two measurements taken on the same subjects by '
              'counting which way each difference goes, and nothing else.\n\n'
              'Use it when the values are ordinal, or when a difference can '
              'be called positive or negative but its size means little: a '
              'rating, a ranking, a judgement. A subject whose two '
              'measurements are equal takes no part.\n\n'
              'It asks less of the data than any other paired test and finds '
              'less in return. Where the size of a difference is meaningful, '
              'the Wilcoxon signed-rank test is more powerful.',
    'layouts': MATCHED,
    'options': (METHOD_EXACT, TAIL_MEDIANS, ALPHA_LEVEL)},
  'Friedman': {
    'category': 'Group comparisons',
    'input': 'matched',
    'title': 'Friedman test',
    'function': 'octave_calc_friedman',
    'detail': 'Compares three or more measurements taken on the same '
              'subjects by ranking them within each subject.\n\n'
              'Use it when each row is one subject measured under every '
              'condition, and the values are at least ordinal. Each subject '
              'ranks the conditions for itself, so differences between '
              'subjects drop out. It answers whether any condition differs; '
              'the pairwise comparisons say which.\n\n'
              'For two measurements use the Wilcoxon signed-rank test. For '
              'independent groups use the Kruskal-Wallis Test.',
    'layouts': MATCHED,
    'options': (
      {'name': 'ctype', 'kind': 'choice', 'label': 'Comparisons:',
       'hint': 'How the p-values of the pairwise comparisons are adjusted.',
       'choices': (('holm', 'Holm'), ('bonferroni', 'Bonferroni'),
                   ('scheffe', 'Scheffe'), ('mvt', 'Multivariate t'),
                   ('hochberg', 'Hochberg'), ('fdr', 'False discovery rate'),
                   ('lsd', 'None')),
       'default': 'holm'},
      ALPHA_LEVEL)},
  'FullFactorial': {
    'category': 'Experimental design',
    'title': 'Full factorial design',
    'function': 'octave_calc_fullfact',
    'input': 'none',
    'detail': 'Writes every combination of the levels of each factor, one '
              'run per row.\n\n'
              'Use it to lay out a study before running it, when every '
              'factor is to be crossed with every other. Three factors of 2, '
              '3 and 3 levels give 18 runs.\n\n'
              'For factors of two levels each, the two-level design is '
              'shorter to ask for.',
    'layouts': (),
    'options': (
      {'name': 'levels', 'kind': 'numbers', 'label': 'Levels per factor:',
       'hint': 'One number per factor, such as 2 3 3.',
       'accepts': 'one whole number per factor, each 2 or more',
       'minimum': 1.0, 'maximum': 1000.0, 'whole': True, 'default': '2 3 3'},)},
  'TwoLevelFactorial': {
    'category': 'Experimental design',
    'title': 'Two-level factorial design',
    'function': 'octave_calc_ff2n',
    'input': 'none',
    'detail': 'Writes every combination of two levels, 0 and 1, of the given '
              'number of factors, one run per row.\n\n'
              'Use it for a screening study where each factor is set low or '
              'high. Five factors give 32 runs, and the count doubles with '
              'each factor added.',
    'layouts': (),
    'options': (
      {'name': 'factors', 'kind': 'number', 'label': 'Factors:',
       'hint': 'Each factor doubles the number of runs.',
       'accepts': 'a whole number from 1 to 15',
       'minimum': 0.0, 'maximum': 16.0, 'whole': True, 'default': '3'},)},
  'SampleSize': {
    'category': 'Experimental design',
    'title': 'Sample size',
    'function': 'octave_calc_sampsize',
    'input': 'none',
    'detail': 'How many observations a test needs to reach a given power '
              'against a stated alternative.\n\n'
              'Use it before collecting data, when you know roughly what '
              'difference is worth detecting and how variable the values '
              'are.\n\n'
              'The two-sample t-test reports the size of each group.',
    'layouts': (),
    'options': (POWER_TEST, NULL_VALUE, NULL_SD,
                {'name': 'p1', 'kind': 'number', 'label': 'Alternative value:',
                 'hint': 'The value worth detecting, as a mean, proportion, '
                         'variance or correlation.',
                 'accepts': 'a number', 'minimum': float ('-inf'),
                 'maximum': float ('inf'), 'default': '6'},
                {'name': 'power', 'kind': 'number', 'label': 'Power:',
                 'hint': 'The chance of detecting it. Must exceed the '
                         'significance level.',
                 'accepts': 'a number greater than 0 and less than 1',
                 'minimum': 0.0, 'maximum': 1.0, 'default': '0.9'},
                ALPHA_LEVEL)},
  'TestPower': {
    'category': 'Experimental design',
    'title': 'Power',
    'function': 'octave_calc_testpower',
    'input': 'none',
    'detail': 'The chance a test of a given size has of detecting a stated '
              'alternative.\n\n'
              'Use it on a study already sized, to see what it can and '
              'cannot show. A low power means a result of no difference says '
              'little.',
    'layouts': (),
    'options': (POWER_TEST, NULL_VALUE, NULL_SD,
                {'name': 'p1', 'kind': 'number', 'label': 'Alternative value:',
                 'hint': 'The value worth detecting, as a mean, proportion, '
                         'variance or correlation.',
                 'accepts': 'a number', 'minimum': float ('-inf'),
                 'maximum': float ('inf'), 'default': '6'},
                SAMPLE_SIZE, ALPHA_LEVEL)},
  'Detectable': {
    'category': 'Experimental design',
    'title': 'Detectable difference',
    'function': 'octave_calc_detectable',
    'input': 'none',
    'detail': 'The smallest alternative a test of a given size can detect '
              'with a given power.\n\n'
              'Use it when the sample size is fixed by what is available, to '
              'see what the study could ever show.',
    'layouts': (),
    'options': (POWER_TEST, NULL_VALUE, NULL_SD,
                {'name': 'power', 'kind': 'number', 'label': 'Power:',
                 'hint': 'The chance of detecting it. Must exceed the '
                         'significance level.',
                 'accepts': 'a number greater than 0 and less than 1',
                 'minimum': 0.0, 'maximum': 1.0, 'default': '0.9'},
                SAMPLE_SIZE, ALPHA_LEVEL)}}


def first_analysis ():
  """The command the dialog opens on: the first analysis of the first
  category that has one."""
  for category in CATEGORIES:
    commands = analyses_of (category)
    if (commands):
      return commands[0]
  return None


def analyses_of (category):
  """The commands of CATEGORY, in order."""
  return tuple (command for command, analysis in ANALYSES.items ()
                if analysis['category'] == category)


def option_defaults (command):
  """What the options of COMMAND hold before the user touches them."""
  return dict ((option['name'], option['default'])
               for option in ANALYSES[command]['options'])


def option_number (option, value):
  """VALUE as the number OPTION takes, from the dialog's text or a number.
  Raises ValueError saying what the option accepts."""
  return option_numbers (option, value)[0]


def option_numbers (option, value):
  """VALUE as the list of numbers OPTION takes, from the dialog's text, where
  they are written one after another, or from numbers already.  Raises
  ValueError saying what the option accepts."""
  what = option['label'].rstrip (':').lower ()
  refusal = ValueError ('the %s must be %s.' % (what, option['accepts']))
  if (option['kind'] == 'number'):
    # One number, where a comma is the decimal point a Greek locale types
    words = [str (value).strip ().replace (',', '.')]
  else:
    words = str (value).replace (',', ' ').replace (';', ' ').split ()
  if (not words or not words[0]):
    raise refusal
  numbers = []
  for word in words:
    try:
      number = float (word)
    except ValueError:
      raise refusal
    if (not (option['minimum'] < number < option['maximum'])):
      raise refusal
    if (option.get ('whole') and number != int (number)):
      raise refusal
    numbers.append (number)
  if (option['kind'] == 'number' and len (numbers) != 1):
    raise refusal
  return numbers


def option_args (command, values):
  """The octave_call arguments for the options of COMMAND, in declared order,
  from VALUES as the dialog holds them.  An option the user has not set takes
  its default.  Raises ValueError on a value the option does not take."""
  args = []
  for option in ANALYSES[command]['options']:
    value = values.get (option['name'], option['default'])
    if (option['kind'] == 'number'):
      args.append ({'type': 'number', 'value': option_number (option, value)})
      continue
    if (option['kind'] == 'numbers'):
      args.append (octave_core.range_arg (
        [[{'kind': 'number', 'value': number}
          for number in option_numbers (option, value)]]))
      continue
    if (value not in [choice for choice, unused in option['choices']]):
      raise ValueError ('%s is not a value of "%s".' % (value, option['name']))
    args.append ({'type': 'string', 'value': value})
  return args


# An analysis function always takes the range, the layout and the group names,
# so that the options an analysis declares follow at fixed positions.  This
# stands for no names at all: empty text, since a range must hold a cell.
NO_NAMES = {'type': 'string', 'value': ''}


def is_name (value):
  """True when VALUE, as getDataArray gives it, is text that cannot be read
  as a number, and so a name."""
  return (isinstance (value, str) and value != ''
          and value.lower () not in octave_core.NUMBER_TEXTS)


def number_cell (value, column, row, allowed):
  """The range cell for VALUE, as getDataArray gives it, at COLUMN and ROW on
  its sheet: a number, Inf, -Inf or NaN written as text, or empty.  Raises
  ValueError, ending with ALLOWED, on any other text."""
  if (isinstance (value, str)):
    if (value == ''):
      return {'kind': 'empty'}
    if (not is_name (value)):
      return {'kind': 'number',
              'value': octave_core.NUMBER_TEXTS[value.lower ()]}
    raise ValueError ('%s holds the text "%s"; %s'
                      % (octave_core.cell_name (column, row), value, allowed))
  return {'kind': 'number', 'value': float (value)}


def header_only ():
  return ValueError ('the input range holds only its header.')


def group_args (rows, by, column, row, kind = 'range'):
  """The arguments for one group per column or, when BY is 'rows', per row,
  from ROWS whose top-left cell is at COLUMN and ROW.  A first row, or first
  column, holding a name is the header, passed as the groups' names.  KIND is
  what those columns or rows hold, which only the refusals say."""
  if (by == 'rows'):
    header = [values[0] for values in rows]
    body = [values[1:] for values in rows]
    left, top = column + 1, row
  else:
    header = list (rows[0])
    body = rows[1:]
    left, top = column, row + 1
  named = any (is_name (value) for value in header)
  if (not named):
    body, left, top = rows, column, row
  if (not body or not body[0]):
    raise header_only ()
  names = NO_NAMES
  if (named):
    names = octave_core.range_arg (
      [[octave_core.plain_cell (value) for value in header]])
  return [octave_core.range_arg (
            [[number_cell (value, left + c, top + r, allowed (by, kind))
              for c, value in enumerate (values)]
             for r, values in enumerate (body)]),
          {'type': 'string', 'value': by}, names]


def labels_args (rows, by, column, row):
  """The arguments for two columns, each value beside the label of its
  group, from ROWS whose top-left cell is at COLUMN and ROW; BY says which
  column holds the labels.  The values go first.  A first row whose value is
  a name is a header, and ignored."""
  if (len (rows[0]) != 2):
    raise ValueError ('grouped by labels, the input range must be two columns '
                      'wide: the values and their group labels.')
  at = 0 if by == 'labels-data' else 1
  start = 1 if is_name (rows[0][1 - at]) else 0
  if (start == len (rows)):
    raise header_only ()
  cells = []
  for r in range (start, len (rows)):
    label = rows[r][at]
    number = number_cell (rows[r][1 - at], column + 1 - at, row + r,
                          allowed (by, 'range'))
    if (number['kind'] == 'number' and label == ''):
      raise ValueError ('%s holds a value with no group label in %s.'
                        % (octave_core.cell_name (column + 1 - at, row + r),
                           octave_core.cell_name (column + at, row + r)))
    cells.append ([number, octave_core.plain_cell (label)])
  return [octave_core.range_arg (cells), {'type': 'string', 'value': 'labels'},
          NO_NAMES]


def factor_args (rows, by, column, row):
  """The arguments for each value beside the two factors it was measured
  under, from ROWS whose top-left cell is at COLUMN and ROW; BY says whether
  the two factor columns come before the values or after them.  The values go
  first, then the two factors.  A first row whose value is a name is a header
  and names the factors."""
  if (len (rows[0]) != 3):
    raise ValueError ('with two factors the input range must be three columns '
                      'wide: the values and the two factors of each.')
  at = 0 if by == 'labels-data' else 1
  value = 2 if at == 0 else 0
  first, second = (0, 1) if at == 0 else (1, 2)
  start = 1 if is_name (rows[0][value]) else 0
  if (start == len (rows)):
    raise header_only ()
  names = NO_NAMES
  if (start):
    names = octave_core.range_arg (
      [[octave_core.plain_cell (rows[0][first]),
        octave_core.plain_cell (rows[0][second])]])
  cells = []
  for r in range (start, len (rows)):
    number = number_cell (rows[r][value], column + value, row + r,
                          allowed (by, 'factors'))
    for which in (first, second):
      if (number['kind'] == 'number' and rows[r][which] == ''):
        raise ValueError ('%s holds a value with no factor in %s.'
                          % (octave_core.cell_name (column + value, row + r),
                             octave_core.cell_name (column + which, row + r)))
    cells.append ([number, octave_core.plain_cell (rows[r][first]),
                   octave_core.plain_cell (rows[r][second])])
  return [octave_core.range_arg (cells), {'type': 'string', 'value': 'labels'},
          names]


def analysis_args (rows, by, column, row, kind = 'range'):
  """The octave_call arguments of an analysis function: the input range ROWS,
  whose top-left cell is at COLUMN and ROW, and how BY says it is laid out,
  for an analysis of that KIND.  Raises ValueError."""
  if (by not in BY):
    raise ValueError ('grouped by must be "columns", "rows", "labels-data" or '
                      '"data-labels".')
  if (kind == 'factors'):
    return factor_args (rows, by, column, row)
  if (by in ('columns', 'rows')):
    return group_args (rows, by, column, row, kind)
  return labels_args (rows, by, column, row)


def results (outputs):
  """The rows of cells an analysis function returned as its only output."""
  return octave_core.output_rows (outputs[0])


def reason (message, function):
  """MESSAGE from Octave without the name of FUNCTION in front of it, which
  names nothing a Calc user has seen."""
  prefix = function + ': '
  return message[len (prefix):] if message.startswith (prefix) else message


def overlaps (first, second):
  """True when two ranges share a cell, each given as its sheet, first column,
  first row, last column and last row."""
  return (first[0] == second[0]
          and first[1] <= second[3] and second[1] <= first[3]
          and first[2] <= second[4] and second[2] <= first[4])
