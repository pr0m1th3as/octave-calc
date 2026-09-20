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
INPUTS = ('range', 'matched', 'factors', 'sample', 'none')

# What a column or a row of the input range holds, by the kind of input.  The
# dialog and every refusal say it in the user's words, since reading matched
# measurements as independent groups, or the other way about, answers a
# question the user did not ask and says nothing about it.
NOUN = {'range': 'group', 'matched': 'measurement',
        'factors': 'factor', 'sample': 'sample'}


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
# shown under the category.  A category joins this list with the analyses
# that fill it; one listed and empty offers the user a door into a room that
# does not exist.  Association tests, Regression models and Multivariate
# analyses are still to be written and are therefore not here.
CATEGORIES = {
  'Group comparisons':
    'Tests whether two or more groups differ, and which of them do.',
  'Distribution fitting':
    'Fits a distribution to a sample, and tests whether it fits.',
  'Random numbers':
    'Draws a sample from a distribution and the parameters you give it.',
  'Experimental design':
    'Plans a study before the data exist: how many observations are needed, '
    'and which combinations to run.'}


# What the list under a category is called, where 'Analysis:' is wrong for
# what it holds.
LIST_LABEL = {'Random numbers': 'Available generators:'}

# Option rows the dialog holds ready, since a control cannot be added once it
# is open.  An analysis may draw no more options than this in them.
OPTION_SLOTS = 8

# The longest note an option row can show beside its label without the field
# to its right cutting it off, measured in characters against the width the
# dialog gives it.  A note is a few words, not a sentence, so this is a
# generous cap and not a squeeze.
NOTE_LIMIT = 24


def category_names ():
  """The categories in the order the dialog lists them."""
  return tuple (CATEGORIES)


def list_label (category):
  """What the list of the analyses of CATEGORY is called."""
  return LIST_LABEL.get (category, 'Analysis:')

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

INF = float ('inf')

# What a distribution calls itself, where that differs from the name makedist
# knows it by.  The generator list and the title of its results read this one,
# the command and the call the other; a test holds the two together against
# the DistributionName the live server gives.
READABLE = {'BirnbaumSaunders': 'Birnbaum-Saunders',
            'ExtremeValue': 'Extreme Value',
            'GeneralizedExtremeValue': 'Generalized Extreme Value',
            'GeneralizedPareto': 'Generalized Pareto',
            'HalfNormal': 'Half Normal',
            'InverseGaussian': 'Inverse Gaussian',
            'Loglogistic': 'Log-Logistic',
            'NegativeBinomial': 'Negative Binomial',
            'tLocationScale': 't Location-Scale'}


def readable (name):
  """What the distribution NAME calls itself."""
  return READABLE.get (name, name)

# What a parameter of a distribution may be, taken from the checkparams its
# own class raises on, which is the rule that holds and not always the wider
# one ParameterRange declares.  A bound the parameter may reach is said with
# 'atleast' or 'atmost'.
ANY = {'minimum': -INF, 'maximum': INF}
POSITIVE = {'minimum': 0.0, 'maximum': INF}
COUNT = {'minimum': 0.0, 'maximum': INF, 'whole': True}
FROM_ZERO = {'minimum': 0.0, 'maximum': INF, 'atleast': True}
FROM_HALF = {'minimum': 0.5, 'maximum': INF, 'atleast': True}
UNIT = {'minimum': 0.0, 'maximum': 1.0, 'atleast': True, 'atmost': True}
PROBABILITY = {'minimum': 0.0, 'maximum': 1.0, 'atmost': True}
TO_TWO = {'minimum': 0.0, 'maximum': 2.0, 'atmost': True}
SKEW = {'minimum': -1.0, 'maximum': 1.0, 'atleast': True, 'atmost': True}

# Every distribution makedist takes whose parameters are all single numbers,
# each drawn from by a generator of its own, listed by its name alone since
# the category already says they draw.  Kernel is not parametric, and
# Multinomial and PiecewiseLinear take vectors, so none of the three can be
# given a number per parameter; a test against the live server holds this
# list to the ones that can.
#
# Each parameter carries the name makedist gives it, the description its
# distribution class gives it, the bounds that class declares, and the value
# makedist holds before it is told otherwise.  Triangular and Uniform declare
# no range, their limits bounding each other rather than themselves, so their
# parameters are open and makedist refuses what the dialog cannot.
GENERATORS = (
  ('Beta',
   'Draws values between 0 and 1, shaped by the two parameters into '
   'anything from a flat spread to a peak near either end.\n\n'
   'Use it for proportions and rates: a success rate, a share, a '
   'probability that is itself uncertain. a pulls the values towards 1 and '
   'b towards 0; equal values are symmetric, and 1 for both is flat.',
   (('a', 'first shape parameter', POSITIVE, '1'),
    ('b', 'second shape parameter', POSITIVE, '1'))),
  ('Binomial',
   'Draws the number of successes in N independent trials, each succeeding '
   'with probability p.\n\n'
   'Use it for counts out of a fixed total: defects in a batch, heads in a '
   'run of tosses, patients responding out of those treated. Every draw is '
   'a whole number from 0 to N.',
   (('N', 'number of trials', COUNT, '1'),
    ('p', 'probability of success', UNIT, '0.5'))),
  ('BirnbaumSaunders',
   'Draws positive values from a distribution built for how long a part '
   'lasts under repeated stress.\n\n'
   'Use it for fatigue life and time to failure. beta is the median life, '
   'and gamma how widely lives scatter about it.',
   (('beta', 'scale', POSITIVE, '1'), ('gamma', 'shape', POSITIVE, '1'))),
  ('Burr',
   'Draws positive values with a heavy right tail, the two shape '
   'parameters setting how heavy.\n\n'
   'Use it for incomes, insurance claims and other quantities where a few '
   'values dwarf the rest. alpha scales, and c and k shape.',
   (('alpha', 'scale', POSITIVE, '1'), ('c', 'first shape', POSITIVE, '1'),
    ('k', 'second shape', POSITIVE, '1'))),
  ('Exponential',
   'Draws positive values that fall away at a constant rate: the wait for '
   'an event that is no more likely for having been waited for.\n\n'
   'Use it for the time between arrivals, the life of something that does '
   'not wear out, and the gaps in a Poisson process. mu is the mean wait.',
   (('mu', 'mean', POSITIVE, '1'),)),
  ('ExtremeValue',
   'Draws the smallest of many values, from a distribution with a long '
   'left tail.\n\n'
   'Use it for minima: the weakest link, the lowest temperature of a year, '
   'the first failure in a set. mu locates it and sigma spreads it. For '
   'maxima use the generalized extreme value.',
   (('mu', 'location', ANY, '0'), ('sigma', 'scale', POSITIVE, '1'))),
  ('Gamma',
   'Draws positive values skewed to the right: the total of a independent '
   'exponential waits of mean b.\n\n'
   'Use it for total waiting times, rainfall and insurance claims. a '
   'shapes and b scales; a of 1 is the exponential.',
   (('a', 'shape', POSITIVE, '1'), ('b', 'scale', POSITIVE, '1'))),
  ('GeneralizedExtremeValue',
   'Draws the largest of many values, the shape deciding which of the '
   'three extreme value families it is.\n\n'
   'Use it for maxima: flood heights, peak loads, record times. k below 0 '
   'gives a bounded tail, 0 the Gumbel, and above 0 a heavy one; sigma '
   'scales and mu locates.',
   (('k', 'shape', ANY, '0'), ('sigma', 'scale', POSITIVE, '1'),
    ('mu', 'location', ANY, '0'))),
  ('GeneralizedPareto',
   'Draws the amount by which a value passes a threshold, given that it '
   'has passed it.\n\n'
   'Use it for the tail of a distribution above a cutoff: losses beyond a '
   'deductible, river levels above a bank. theta is the threshold, sigma '
   'scales, and k above 0 gives a heavy tail.',
   (('k', 'shape', ANY, '1'), ('sigma', 'scale', POSITIVE, '1'),
    ('theta', 'location', ANY, '1'))),
  ('HalfNormal',
   'Draws the size of a normal value with its sign discarded, so every '
   'draw is at mu or above it.\n\n'
   'Use it for magnitudes and distances from a target, where the direction '
   'does not matter, and for a quantity that cannot be negative. sigma is '
   'the scale of the normal it folds.',
   (('mu', 'location', ANY, '0'), ('sigma', 'scale', POSITIVE, '1'))),
  ('InverseGaussian',
   'Draws positive values skewed to the right: the time a drifting random '
   'walk first reaches a level.\n\n'
   'Use it for first passage times, reaction times and durations with a '
   'sharp rise and a long tail. mu is the mean and lambda how tightly the '
   'values gather.',
   (('mu', 'mean', POSITIVE, '1'), ('lambda', 'shape', POSITIVE, '1'))),
  ('Logistic',
   'Draws values in a symmetric bell, a little heavier in the tails than '
   'the normal.\n\n'
   'Use it where a normal is nearly right but extremes are more common '
   'than it allows, and as the noise behind logistic regression. mu '
   'centres and sigma spreads.',
   (('mu', 'location', ANY, '0'), ('sigma', 'scale', POSITIVE, '1'))),
  ('Loglogistic',
   'Draws positive values whose logarithm is logistic: skewed right, with '
   'a heavy tail.\n\n'
   'Use it for survival times and event durations where the risk rises and '
   'then falls. mu and sigma are the mean and scale of the logarithm, not '
   'of the values.',
   (('mu', 'log mean', FROM_ZERO, '0'),
    ('sigma', 'log scale', POSITIVE, '1'))),
  ('Lognormal',
   'Draws positive values whose logarithm is normal: skewed right, with a '
   'long tail.\n\n'
   'Use it for quantities built by multiplying: incomes, particle sizes, '
   'concentrations, times that compound. mu and sigma are the mean and '
   'standard deviation of the logarithm, not of the values.',
   (('mu', 'log mean', ANY, '0'),
    ('sigma', 'log standard deviation', POSITIVE, '1'))),
  ('Loguniform',
   'Draws positive values whose logarithm is spread evenly between the two '
   'limits.\n\n'
   'Use it where a quantity is as likely to be near 1 as near 1000, which '
   'is how an unknown scale is usually treated: a rate, a tolerance, a '
   'search over orders of magnitude.',
   (('Lower', 'lower limit', POSITIVE, '1'),
    ('Upper', 'upper limit', POSITIVE, '4'))),
  ('Nakagami',
   'Draws positive values from a distribution built for the strength of a '
   'radio signal that has faded.\n\n'
   'Use it for signal amplitude over a channel with several paths. mu sets '
   'how deep the fading is, from 0.5 for the worst case upward, and omega '
   'the mean power.',
   (('mu', 'shape', FROM_HALF, '1'), ('omega', 'spread', POSITIVE, '1'))),
  ('NegativeBinomial',
   'Draws the number of failures before the Rth success, each trial '
   'succeeding with probability P.\n\n'
   'Use it for counts that vary more than a Poisson allows: accidents, '
   'purchases, reads of a gene. Every draw is a whole number of 0 or more.',
   (('R', 'number of successes', POSITIVE, '1'),
    ('P', 'probability of success', PROBABILITY, '0.5'))),
  ('Normal',
   'Draws values that cluster about a mean and fall away symmetrically '
   'either side of it.\n\n'
   'Use it for measurement error, for a quantity made of many small '
   'independent effects, and as the default where nothing suggests '
   'otherwise. mu sets the centre and sigma the spread.',
   (('mu', 'mean', ANY, '0'),
    ('sigma', 'standard deviation', POSITIVE, '1'))),
  ('Poisson',
   'Draws the number of events in a fixed span, where they happen '
   'independently at a steady rate.\n\n'
   'Use it for counts with no upper limit: calls in an hour, defects in a '
   'metre, arrivals in a day. lambda is both the mean count and its '
   'variance.',
   (('lambda', 'rate', POSITIVE, '1'),)),
  ('Rayleigh',
   'Draws the length of a two-dimensional vector whose two components are '
   'independent normal values.\n\n'
   'Use it for wind speeds, wave heights and the magnitude of a signal of '
   'random phase. B is the scale of the components.',
   (('B', 'scale', POSITIVE, '1'),)),
  ('Rician',
   'Draws the magnitude of a signal that has a steady part as well as a '
   'random one.\n\n'
   'Use it for a radio signal with a direct path among the scattered ones, '
   'and for magnitudes in magnetic resonance images. s is the steady part '
   'and sigma the noise; an s of 0 gives the Rayleigh.',
   (('s', 'noncentrality', FROM_ZERO, '1'),
    ('sigma', 'scale', POSITIVE, '1'))),
  ('Stable',
   'Draws values from a family whose tails are so heavy that, anywhere but '
   'at an alpha of 2, the variance does not exist.\n\n'
   'Use it for financial returns and other quantities with the occasional '
   'enormous value. alpha sets the tail, 2 being the normal; beta the '
   'skew, gam the scale and delta the location.',
   (('alpha', 'first shape parameter', TO_TWO, '2'),
    ('beta', 'second shape parameter', SKEW, '0'),
    ('gam', 'scale', POSITIVE, '1'), ('delta', 'location', ANY, '0'))),
  ('tLocationScale',
   'Draws values in a symmetric bell with heavier tails than the normal, '
   'growing lighter as nu rises.\n\n'
   'Use it where extremes are more common than a normal allows: financial '
   'returns, small samples, data with the occasional outlier. mu centres '
   'and sigma scales; an nu above about 30 is close to normal.',
   (('mu', 'location', ANY, '0'), ('sigma', 'scale', POSITIVE, '1'),
    ('nu', 'degrees of freedom', POSITIVE, '5'))),
  ('Triangular',
   'Draws values between A and C, peaking at B, with a straight line '
   'either side of the peak.\n\n'
   'Use it where all that is known is a lowest, a likeliest and a highest '
   'value, which is how project estimates and risk models are usually '
   'given. A, B and C must rise in that order.',
   (('A', 'lower limit', ANY, '0'), ('B', 'peak location', ANY, '0.5'),
    ('C', 'upper limit', ANY, '1'))),
  ('Uniform',
   'Draws values spread evenly between the two limits, none of them more '
   'likely than another.\n\n'
   'Use it for a quantity known only to lie in a range, for rounding '
   'error, and as the raw material other draws are built from. Lower must '
   'be below Upper.',
   (('Lower', 'lower limit', ANY, '0'),
    ('Upper', 'upper limit', ANY, '1'))),
  ('Weibull',
   'Draws positive values whose failure rate rises, falls or holds steady '
   'as the shape B decides.\n\n'
   'Use it for time to failure and for material strength. A B below 1 is '
   'early failure, 1 the exponential and above 1 wearing out; A is the '
   'scale.',
   (('A', 'scale', POSITIVE, '1'), ('B', 'shape', POSITIVE, '1'))))

# The layouts an analysis of one sample takes: a column of values, or a row.
SAMPLE = ('columns', 'rows')

# The distributions fitdist takes, in its own order.  A test asks the live
# server for the list and compares, so that a distribution gained or lost in
# statistics is caught here rather than by a user.
FITTED = ('Beta', 'Binomial', 'BirnbaumSaunders', 'Burr', 'Exponential',
          'ExtremeValue', 'Gamma', 'GeneralizedExtremeValue',
          'GeneralizedPareto', 'HalfNormal', 'InverseGaussian', 'Kernel',
          'Logistic', 'Loglogistic', 'Lognormal', 'Nakagami',
          'NegativeBinomial', 'Normal', 'Poisson', 'Rayleigh', 'Rician',
          'Stable', 'tLocationScale', 'Weibull')

TAIL_MEANS_SAMPLE = {'name': 'tail', 'kind': 'choice',
                     'label': 'Alternative:',
                     'hint': "What the test is prepared to find, the sample "
                             "against the value.",
                     'choices': (('both', 'the means differ'),
                                 ('right', "the sample's mean is greater"),
                                 ('left', "the sample's mean is smaller")),
                     'default': 'both'}

# Twenty-four distributions are too many to drop open over the rows beneath
# them, so this one is drawn as a list of its own that scrolls.
DISTRIBUTION_FIT = {'name': 'distname', 'kind': 'choice',
                    'label': 'Distribution:',
                    'hint': 'The distribution to fit to the sample.',
                    'choices': tuple ((name, name) for name in FITTED),
                    'rows': 4, 'default': 'Normal'}

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
#   listed    what the list calls it, where that is shorter than the title;
#             the title itself otherwise
#   function  the Octave function in the octave folder
#   detail    what it does and when to use it, shown under the list
#   input     'range', the analysis reads the cells of an input range, or
#             'none', it takes its options alone and reads no cells
#   layouts   the ways it takes its input range, from BY, or () when it reads
#             no cells
#   sized     where an analysis takes its size from the results range, the
#             two options that range replaces, rows first; absent otherwise.
#             The dialog draws them as the Rows and Columns fields under the
#             results range, in place of the size the range itself gives
#   seeded    where an analysis takes a seed, the option the dialog draws as
#             the Seed field under the size; absent otherwise
#   heading   what the option rows are called, where 'Options:' is wrong for
#             what they hold
#   options   what the user chooses besides the ranges, passed to the function
#             after the range, the layout and the names, in declared order.
#             Each carries 'name', 'label', 'hint', 'default' and a 'kind':
#             'choice' holds 'choices', ((value, label), ...), and reaches the
#             function as text; 'number' holds 'minimum', 'maximum' and
#             'accepts', the refusal's words, and reaches it as a number,
#             whole when it holds 'whole', and the bound itself allowed where
#             it holds 'atleast' or 'atmost'; 'numbers' holds the same and
#             reaches the function as a range of one row; 'radios' holds two
#             'choices' and is drawn as a button each, one above the other,
#             where a list of two reads as more than it is; 'fixed' is never
#             drawn and reaches the function as its default, as text
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
  'Normality': {
    'category': 'Distribution fitting',
    'input': 'sample',
    'title': 'Tests of normality',
    'function': 'octave_calc_normality',
    'detail': 'Tests whether one sample could have come from a normal '
              'distribution, by four tests at once.\n\n'
              'Use it before a t-test or an ANOVA, which assume it, or '
              'whenever the shape of the data is the question. The four '
              'weigh different departures from normality, so they are all '
              'run and all reported rather than made to be chosen '
              'between.\n\n'
              'Lilliefors and Jarque-Bera read their p-value from a table '
              'and report its edge where the value falls outside; the '
              'results say so when that happens.',
    'layouts': SAMPLE,
    'options': (ALPHA_LEVEL,)},
  'Chi2gof': {
    'category': 'Distribution fitting',
    'input': 'sample',
    'title': 'Goodness of fit',
    'function': 'octave_calc_chi2gof',
    'detail': 'Fits a distribution to one sample, counts the sample into '
              'bins, and tests whether each bin holds as many values as the '
              'fit expects.\n\n'
              'Use it to judge a whole distribution rather than one feature '
              'of it, and for counts and other data the normality tests do '
              'not suit. It needs enough values that each bin expects a '
              'few.\n\n'
              'Bins that expect too little are joined to their neighbours, '
              'so the bins counted may be fewer than the bins asked for, '
              'and more bins does not always mean more of them counted.',
    'layouts': SAMPLE,
    'options': (DISTRIBUTION_FIT,
                {'name': 'nbins', 'kind': 'number', 'label': 'Bins:',
                 'hint': 'How many bins to count the sample into. 10 by '
                         'default.',
                 'accepts': 'a whole number of 2 or more',
                 'minimum': 1.0, 'maximum': float ('inf'), 'whole': True,
                 'default': '10'},
                ALPHA_LEVEL)},
  'Fitdist': {
    'category': 'Distribution fitting',
    'input': 'sample',
    'title': 'Distribution fitting',
    'function': 'octave_calc_fitdist',
    'detail': 'Fits a distribution to one sample and reports each parameter '
              'with a confidence interval.\n\n'
              'Use it to put a shape and a scale on data you will go on to '
              'model, simulate or compare against, or to read off the '
              'quantiles of the fit rather than of the sample.\n\n'
              'Goodness of fit says whether the fit is any good; this says '
              'what the fit is. The curve, where asked for, gives the '
              'density and the cumulative probability of the fitted '
              'distribution, which is the only way to reach them once the '
              'fit is a block of cells.',
    'layouts': SAMPLE,
    'options': (DISTRIBUTION_FIT,
                {'name': 'curve', 'kind': 'radios', 'label': 'Curve at:',
                 'hint': 'Where the curve is read.',
                 'choices': (('sample', 'at each value of the sample'),
                             ('grid', 'at a hundred even points')),
                 'default': 'sample'},
                {'name': 'parts', 'kind': 'checks', 'label': 'Curve holds:',
                 'hint': 'Tick none of them and the fit is written alone.',
                 'choices': (('pdf', 'probability density'),
                             ('cdf', 'cumulative probability')),
                 'default': ''},
                ALPHA_LEVEL)},
  'Isoutlier': {
    'category': 'Distribution fitting',
    'input': 'sample',
    'title': 'Outliers',
    'function': 'octave_calc_isoutlier',
    'detail': 'Finds the values of one sample that sit far enough from the '
              'centre to be called outliers, and says where each one is.\n\n'
              'Use it to check data before an analysis that a single wild '
              'value would carry, and to find the cell that holds it. Each '
              'outlier is reported with the row of the input range it came '
              'from.\n\n'
              'The median method is the safest default, since the median '
              'and the median deviation are not themselves moved by the '
              'values being looked for. The mean method is; Grubbs and GESD '
              'assume the rest of the data is normal.',
    'layouts': SAMPLE,
    'options': (
      {'name': 'method', 'kind': 'choice', 'label': 'Method:',
       'hint': 'How far from what centre a value must sit.',
       'choices': (('median', 'median deviations from the median'),
                   ('mean', 'standard deviations from the mean'),
                   ('quartiles', 'interquartile ranges from the quartiles'),
                   ('grubbs', "Grubbs' test"),
                   ('gesd', 'generalized extreme Studentized deviate')),
       'default': 'median'},
      {'name': 'factor', 'kind': 'number', 'label': 'Factor:',
       'hint': "How far, in the units the method counts in.  0 leaves the "
               "method its own.",
       'accepts': 'a number of 0 or more', 'minimum': -1.0,
       'maximum': float ('inf'), 'default': '0'})},
  'Ttest1': {
    'category': 'Group comparisons',
    'input': 'sample',
    'title': 'One-sample t-test',
    'function': 'octave_calc_ttest1',
    'detail': 'Compares the mean of one sample against a value you name.\n\n'
              'Use it when there is one group and a figure it is meant to '
              'meet: a target, a specification, a published mean, or zero '
              'for differences you have worked out yourself. It answers '
              'whether the sample mean differs from that value, and by how '
              'much, with a confidence interval for the difference.\n\n'
              'For two independent groups use the two-sample t-test, and for '
              'two measurements of the same subjects the paired t-test. When '
              'the data are skewed or few, the Wilcoxon signed-rank test is '
              'safer.',
    'layouts': SAMPLE,
    'options': (
      {'name': 'nullmean', 'kind': 'number', 'label': 'Compare with:',
       'hint': 'The mean the sample is tested against. 0 by default.',
       'accepts': 'a number', 'minimum': float ('-inf'),
       'maximum': float ('inf'), 'default': '0'},
      TAIL_MEANS_SAMPLE, ALPHA_LEVEL)},
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


def accepts_text (bounds):
  """What a parameter of those BOUNDS accepts, as a refusal ends."""
  low, high = bounds['minimum'], bounds['maximum']
  noun = 'a whole number' if bounds.get ('whole') else 'a number'
  if (bounds.get ('atleast') and bounds.get ('atmost')):
    return '%s from %g to %g' % (noun, low, high)
  under = ('' if high == INF else
           'no more than %g' % high if bounds.get ('atmost')
           else 'less than %g' % high)
  over = ('' if low == -INF else
          '%g or more' % low if bounds.get ('atleast')
          else 'greater than %g' % low)
  if (over and under):
    return '%s %s and %s' % (noun, over, under)
  return '%s %s' % (noun, over or under) if (over or under) else noun


# The size of the draw and the seed, which every generator takes and the
# dialog draws under the results range rather than among the parameters.
# A hint says what the field is for, in a sentence the user could have
# written; the tooltip says the rest.  A generator returns the numbers and
# nothing else, so the size asked for is the size written.
DRAW_ROWS = {'name': 'nrows', 'kind': 'number', 'label': 'Rows:',
             'hint': 'Set the size of the returned cell range.',
             'help': 'Set the size of the returned cell range.  A results '
                     'range of more than one cell sets it instead.',
             'accepts': 'a whole number of 1 or more', 'minimum': 0.0,
             'maximum': INF, 'whole': True, 'default': '10'}

DRAW_COLS = dict (DRAW_ROWS, name = 'ncols', label = 'Columns:',
                  default = '1')

DRAW_SEED = {'name': 'seed', 'kind': 'numbers', 'label': 'Seed:',
             'hint': 'Set a seed to draw the same numbers again.  Leave it '
                     'empty and one is chosen for you.',
             'help': 'Set a seed to draw the same numbers again.  Leave it '
                     'empty and one is chosen at the time.  The seed is '
                     'written above the numbers either way.',
             'accepts': 'a whole number of 0 or more, or nothing at all',
             'minimum': -1.0, 'maximum': INF, 'whole': True,
             'optional': True, 'default': ''}

# A generator each, from GENERATORS.  The command a macro dispatches is
# Random and the name makedist knows the distribution by; the list shows
# that name alone, and the sheet the whole title.
for _name, _detail, _parameters in GENERATORS:
  ANALYSES['Random%s' % _name] = {
    'category': 'Random numbers',
    'input': 'none',
    'title': '%s random numbers' % readable (_name),
    'listed': readable (_name),
    'function': 'octave_calc_random',
    'detail': _detail,
    'layouts': (),
    'sized': ('nrows', 'ncols'),
    'seeded': 'seed',
    'heading': 'Distribution parameters:',
    'options': (
      {'name': 'distname', 'kind': 'fixed', 'label': 'Distribution:',
       'hint': 'The distribution drawn from.', 'default': _name},
      DRAW_ROWS, DRAW_COLS, DRAW_SEED)
      + tuple (dict (_bounds, name = _parameter, kind = 'number',
                     label = '%s:' % _parameter, note = _description,
                     hint = '%s.  Takes %s.'
                            % (_description[:1].upper () + _description[1:],
                               accepts_text (_bounds)),
                     accepts = accepts_text (_bounds), default = _default)
               for _parameter, _description, _bounds, _default
               in _parameters)}


def listed (command):
  """What the list calls COMMAND."""
  analysis = ANALYSES[command]
  return analysis.get ('listed', analysis['title'])


def slotted (command):
  """The options of COMMAND the dialog draws in its option rows: those it
  does not draw beside the results range, and those it draws at all."""
  analysis = ANALYSES[command]
  aside = set (analysis.get ('sized', ()))
  aside.add (analysis.get ('seeded'))
  return tuple (option for option in analysis['options']
                if option['kind'] != 'fixed' and option['name'] not in aside)


def slots (option):
  """Option rows OPTION takes up.  A list drawn open rather than dropped
  down, and a stack of buttons, are each as tall as two of them; a stack of
  boxes is as tall as it has boxes, and never less than two."""
  if (option['kind'] == 'checks'):
    return max (2, len (option['choices']))
  return 2 if (option.get ('rows') or option['kind'] == 'radios') else 1


def ticked (option, value):
  """The choices of a 'checks' option that VALUE holds, in declared order.
  VALUE is the ticked keys with a space between them, and nothing at all
  where none is ticked."""
  held = str (value).split ()
  return tuple (choice for choice, unused in option['choices']
                if choice in held)


def slot_places (command):
  """Which option row each of COMMAND's drawn options starts at."""
  places, row = [], 0
  for option in slotted (command):
    places.append (row)
    row += slots (option)
  return places


def heading (command):
  """What the option rows of COMMAND are called."""
  return ANALYSES[command].get ('heading', 'Options:')


def option_named (command, name):
  """The option of COMMAND called NAME."""
  for option in ANALYSES[command]['options']:
    if (option['name'] == name):
      return option
  raise KeyError ('%s declares no option "%s".' % (command, name))


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
    if (option.get ('optional')):
      return []
    raise refusal
  numbers = []
  for word in words:
    try:
      number = float (word)
    except ValueError:
      raise refusal
    over = (number >= option['minimum'] if option.get ('atleast')
            else number > option['minimum'])
    under = (number <= option['maximum'] if option.get ('atmost')
             else number < option['maximum'])
    if (not (over and under)):
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
    if (option['kind'] == 'fixed'):
      args.append ({'type': 'string', 'value': option['default']})
      continue
    # Ticked boxes reach the function as their keys with a space between
    if (option['kind'] == 'checks'):
      args.append ({'type': 'string',
                    'value': ' '.join (ticked (option, value))})
      continue
    if (option['kind'] == 'number'):
      args.append ({'type': 'number', 'value': option_number (option, value)})
      continue
    if (option['kind'] == 'numbers'):
      numbers = option_numbers (option, value)
      if (not numbers):
        args.append (NOTHING)
        continue
      args.append (octave_core.range_arg (
        [[{'kind': 'number', 'value': number} for number in numbers]]))
      continue
    if (value not in [choice for choice, unused in option['choices']]):
      raise ValueError ('%s is not a value of "%s".' % (value, option['name']))
    args.append ({'type': 'string', 'value': value})
  return args


# An analysis function always takes the range, the layout and the group names,
# so that the options an analysis declares follow at fixed positions.  This
# stands for no names at all: empty text, since a range must hold a cell.
NO_NAMES = {'type': 'string', 'value': ''}

# What an option the user left empty reaches Octave as, where the option says
# it may be left empty.  A range must hold a cell, so this is empty text, and
# the analysis reads it as nothing given.
NOTHING = {'type': 'string', 'value': ''}


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
