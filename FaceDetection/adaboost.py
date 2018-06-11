"""
Programmer  :   EOF
E-mail      :   jasonleaster@163.com
Cooperator  :   Wei Chen.
Date        :   2015.11.22
File        :   adaboost.py
License     :   MIT License

File Description:
    AdaBoost is a machine learning meta-algorithm.
That is the short for "Adaptive Boosting".

Thanks Wei Chen. Without him, I can't understand AdaBoost in this short time.
We help each other and learn this algorithm.

"""

from config import DEBUG_MODEL
from config import USING_CASCADE

from config import LABEL_POSITIVE
from config import LABEL_NEGATIVE

from config import EXPECTED_TPR
from config import EXPECTED_FPR

from config import ROC_FILE

from weakClassifier import WeakClassifier
from matplotlib     import pyplot
from haarFeature    import Feature

import numpy
import time
import pylab
import math


def getCachedAdaBoost(mat = None, label = None, filename = "", limit = 0):
    """
        Construct a AdaBoost object with cached data
        from file @ADABOOST_FILE """

    #fileObj = open(filename, "a+")
    fileObj = open(filename)
    #print(fileObj)
    print("Constructing AdaBoost from existed model data")

    tmp = fileObj.readlines()
    if len(tmp) == 0:
        raise ValueError("There is no cached AdaBoost model")

    weakerNum = len(tmp) / 4
    model     = AdaBoost(train = False, limit = weakerNum)

    if limit < weakerNum:
        model.weakerLimit = limit
    else:
        model.weakerLimit = weakerNum

    for i in range(0, len(tmp), 4):

        alpha, dimension, direction, threshold = None, None, None, None

        for j in range(i, i + 4):
            if   (j % 4) == 0:
                alpha     = float(tmp[j])
            elif (j % 4) == 1:
                dimension = int(tmp[j])
            elif (j % 4) == 2:
                direction = float(tmp[j])
            elif (j % 4) == 3:
                threshold = float(tmp[j])

        classifier = model.Weaker(train = False)
        classifier.constructor(dimension, direction, threshold)
        classifier._mat = mat
        classifier._label = label

        if mat is not None:
            classifier.sampleNum = mat.shape[1]
        #print('i=', i)
        model.G[int(i/4)]     = classifier
        model.alpha[int(i/4)] = alpha
        model.N         += 1

    model._mat = mat
    model._label = label
    if model.N > limit:
        model.N    = limit

    if label is not None:
        model.samplesNum = len(label)

    print("Construction finished")
    fileObj.close()

    return model


class AdaBoost:
    """
        Parameter:
        @Mat    :   A matrix(or two dimension array) which's size is
                    (row    = number of features,
                    column  = number of total sample)
        @Tag    :   A vector(or one dimension array) which's size is the
                    same as the number of total sample
        @classifier: Object. A instance of weaker classifier.

        @train  :   A bool value. If it's False, it means that user want to
                    get a instance of this class object from cached data
        @limit  :   A integer. The limitation of training times."""


    def __init__(self, Mat = None, Tag = None, classifier = WeakClassifier, train = True, limit = 4):
        if train == True:
            self._mat   = Mat
            self._label = Tag

            self.samplesDim, self.samplesNum = self._mat.shape

            # Make sure that the inputted data's dimension is right.
            assert self.samplesNum == self._label.size

            self.posNum = numpy.count_nonzero(self._label == LABEL_POSITIVE)
            self.negNum = numpy.count_nonzero(self._label == LABEL_NEGATIVE)

            # Initialization of weight
            pos_W = [1.0/(2 * self.posNum) for i in range(self.posNum)]

            neg_W = [1.0/(2 * self.negNum) for i in range(self.negNum)]
            self.W = numpy.array(pos_W + neg_W)

            self.accuracy = []

        self.Weaker = classifier
        limit = math.floor(limit)
        self.weakerLimit = limit
        #print('limit=', limit)

        self.G      = [None for _ in range(limit)]
        self.alpha  = [  0  for _ in range(limit)]
        self.N      = 0
        self.detectionRate = 0.

        # true positive rate
        self.tpr = 0.
        # false positive rate
        self.fpr = 0.

        self.th  = 0.


    def is_good_enough(self):

        output = self.prediction(self._mat, self.th)

        correct = numpy.count_nonzero(output == self._label)/(self.samplesNum*1.)
        self.accuracy.append( correct)

        self.detectionRate = numpy.count_nonzero(output[0:self.posNum] == LABEL_POSITIVE) * 1./ self.posNum

        Num_tp = 0 # Number of true positive
        Num_fn = 0 # Number of false negative
        Num_tn = 0 # Number of true negative
        Num_fp = 0 # Number of false positive
        for i in range(self.samplesNum):
            if self._label[i] == LABEL_POSITIVE:
                if output[i] == LABEL_POSITIVE:
                    Num_tp += 1
                else:
                    Num_fn += 1
            else:
                if output[i] == LABEL_POSITIVE:
                    Num_fp += 1
                else:
                    Num_tn += 1

        self.tpr = Num_tp * 1./(Num_tp + Num_fn)
        self.fpr = Num_fp * 1./(Num_tn + Num_fp)

        if self.tpr > EXPECTED_TPR and self.fpr < EXPECTED_FPR:
            return True

    def train(self):
        """
        function @train() is the main process which run
        AdaBoost algorithm."""

        adaboost_start_time = time.time()

        for m in range(self.weakerLimit):
            self.N += 1

            if DEBUG_MODEL == True:
                weaker_start_time = time.time()

            self.G[m] = self.Weaker(self._mat, self._label, self.W)
            
            errorRate = self.G[m].train()

            if DEBUG_MODEL == True:
                print("Time for training WeakClassifier:", \
                        time.time() - weaker_start_time)

            if errorRate < 0.0001:
                errorRate = 0.0001

            beta = errorRate / (1 - errorRate)
            self.alpha[m] = numpy.log(1/beta)

            output = self.G[m].prediction(self._mat)

            for i in range(self.samplesNum):
                #self.W[i] *= numpy.exp(-self.alpha[m] * self._label[i] * output[i])
                if self._label[i] == output[i]:
                    self.W[i] *=  beta

            self.W /= sum(self.W)

            if USING_CASCADE is True:
                self.th, self.detectionRate = self.findThreshold(EXPECTED_TPR)

            if self.is_good_enough():
                print ((self.N) ," weak classifier is enough to ",)
                print ("meet the request which given by user.")
                print ("Training Done :)")
                break

            if DEBUG_MODEL is True:
                print ("weakClassifier:", self.N)
                print ("errorRate     :", errorRate)
                print ("accuracy      :", self.accuracy[-1])
                print ("detectionRate :", self.detectionRate)
                print ("AdaBoost's Th :", self.th)
                print ("alpha         :", self.alpha[m])

        #self.showErrRates()
        #self.showROC()

        print("The time cost of training this AdaBoost model:",\
                time.time() - adaboost_start_time)

        output = self.prediction(self._mat, self.th)
        return output, self.fpr


    def grade(self, Mat):

        #Mat = numpy.array(Mat)

        sampleNum = Mat.shape[1]

        output = numpy.zeros(sampleNum, dtype = numpy.float16)

        for i in range(self.N):
            output += self.G[i].prediction(Mat) * self.alpha[i]

        return output


    def prediction(self, Mat, th = None):

        #Mat = numpy.array(Mat)

        output = self.grade(Mat)
            
        if th == None:
            th = self.th

        """
        # Don't do this! Bug!! the first statement will rewrite the output
        output[output > th]  = LABEL_POSITIVE
        output[output <= th] = LABEL_NEGATIVE
        """

        for i in range(len(output)):
            if output[i] > th:
                output[i] = LABEL_POSITIVE
            else:
                output[i] = LABEL_NEGATIVE

        return output


    def findThreshold(self, expected_tpr):
        detectionRate = 0.
        best_th       = None

        low_bound = -sum(self.alpha)
        up__bound = +sum(self.alpha)
        step      = -0.1
        threshold = numpy.arange(up__bound - step, low_bound + step, step)

        for t in range(threshold.size):

            output = self.prediction(self._mat, threshold[t])

            Num_tp = 0 # Number of true positive
            Num_fn = 0 # Number of false negative
            Num_tn = 0 # Number of true negative
            Num_fp = 0 # Number of false positive
            for i in range(self.samplesNum):
                if self._label[i] == LABEL_POSITIVE:
                    if output[i] == LABEL_POSITIVE:
                        Num_tp += 1
                    else:
                        Num_fn += 1
                else:
                    if output[i] == LABEL_POSITIVE:
                        Num_fp += 1
                    else:
                        Num_tn += 1

            tpr = Num_tp * 1./(Num_tp + Num_fn)
            fpr = Num_fp * 1./(Num_tn + Num_fp)

            if tpr >= expected_tpr:

                detectionRate = numpy.count_nonzero(output[0:self.posNum] == LABEL_POSITIVE) * 1./ self.posNum

                best_th = threshold[t]
                break

        return best_th, detectionRate

    def showErrRates(self):

        pyplot.title("The changes of accuracy (Figure by Jason Leaster)")
        pyplot.xlabel("Iteration times")
        pyplot.ylabel("Accuracy of Prediction")
        pyplot.plot([i for i in range(self.N)],
                    self.accuracy, '-.', 
                    label = "Accuracy * 100%")
        pyplot.axis([0., self.N, 0, 1.])

        if DEBUG_MODEL == True:
            pyplot.show()
        else:
            pyplot.savefig("accuracyflow.jpg")

    def showROC(self):
        best_tpr = 0.
        best_fpr = 1.
        best_th  = None

        low_bound = -sum(self.alpha) * 0.5
        up__bound = +sum(self.alpha) * 0.5
        step      = 0.1
        threshold = numpy.arange(low_bound, up__bound, step)

        tprs      = numpy.zeros(threshold.size, dtype = numpy.float16)
        fprs      = numpy.zeros(threshold.size, dtype = numpy.float16)

        for t in range(threshold.size):

            output = self.prediction(self._mat, threshold[t])

            Num_tp = 0 # Number of true positive
            Num_fn = 0 # Number of false negative
            Num_tn = 0 # Number of true negative
            Num_fp = 0 # Number of false positive
            for i in range(self.samplesNum):
                if self._label[i] == LABEL_POSITIVE:
                    if output[i] == LABEL_POSITIVE:
                        Num_tp += 1
                    else:
                        Num_fn += 1
                else:
                    if output[i] == LABEL_POSITIVE:
                        Num_fp += 1
                    else:
                        Num_tn += 1

            tpr = Num_tp * 1./(Num_tp + Num_fn)
            fpr = Num_fp * 1./(Num_tn + Num_fp)

            # if tpr >= best_tpr and fpr <= best_fpr:
            #     best_tpr = tpr
            #     best_fpr = fpr
            #     best_th  = threshold[t]

            tprs[t] = tpr
            fprs[t] = fpr

        fileObj = open(ROC_FILE, "a+")
        for t, f, th in zip(tprs, fprs, threshold):
            fileObj.write(str(t) + "\t" + str(f) + "\t" + str(th) + "\n")

        fileObj.flush()
        fileObj.close()

        pyplot.title("The ROC curve")
        pyplot.plot(fprs, tprs, "-r", linewidth = 1)
        pyplot.xlabel("fpr")
        pyplot.ylabel("tpr")
        pyplot.axis([-0.02, 1.1, 0, 1.1])
        if DEBUG_MODEL == True:
            pyplot.show()
        else:
            pyplot.savefig("roc.jpg")

    def saveModel(self, filename):
        """
            function @saveModel save the key data member of AdaBoost
        into a template file @ADABOOST_FILE
        """
        fileObj = open(filename, "a+")

        for m in range(self.N):
            fileObj.write(str(self.alpha[m]) + "\n")
            fileObj.write(str(self.G[m].opt_dimension) + "\n")
            fileObj.write(str(self.G[m].opt_direction) + "\n")
            fileObj.write(str(self.G[m].opt_threshold) + "\n")

        fileObj.flush()
        fileObj.close()

    def makeClassifierPic(self):
        from config import TRAINING_IMG_HEIGHT
        from config import TRAINING_IMG_WIDTH
        from config import WHITE
        from config import BLACK
        from config import FIGURES

        from config import HAAR_FEATURE_TYPE_I
        from config import HAAR_FEATURE_TYPE_II
        from config import HAAR_FEATURE_TYPE_III
        from config import HAAR_FEATURE_TYPE_IV
        from config import HAAR_FEATURE_TYPE_V

        IMG_WIDTH  = TRAINING_IMG_WIDTH
        IMG_HEIGHT = TRAINING_IMG_HEIGHT

        haar = Feature(IMG_WIDTH, IMG_HEIGHT)

        featuresAll = haar.features
        selFeatures = [] # selected features

        for n in range(self.N):
            selFeatures.append(featuresAll[self.G[n].opt_dimension])

        classifierPic = numpy.zeros((IMG_HEIGHT, IMG_WIDTH))

        for n in range(self.N):
            feature   = selFeatures[n]
            alpha     = self.alpha[n]
            direction = self.G[n].opt_direction

            (types, x, y, width, height) = feature

            image = numpy.array([[155 for i in range(IMG_WIDTH)] for j in range(IMG_HEIGHT)])

            assert x >= 0 and x < IMG_WIDTH
            assert y >= 0 and y < IMG_HEIGHT
            assert width > 0 and height > 0

            if direction == +1:
                black = BLACK
                white = WHITE
            else:
                black = WHITE
                white = BLACK

            if types == HAAR_FEATURE_TYPE_I:
                for i in range(y, y + height * 2):
                    for j in range(x, x + width):
                        if i < y + height:
                            image[i][j] = black
                        else:
                            image[i][j] = white

            elif types == HAAR_FEATURE_TYPE_II:
                for i in range(y, y + height):
                    for j in range(x, x + width * 2):
                        if j < x + width:
                            image[i][j] = white
                        else:
                            image[i][j] = black

            elif types == HAAR_FEATURE_TYPE_III:
                for i in range(y, y + height):
                    for j in range(x, x + width * 3):
                        if j >= (x + width) and j < (x + width * 2):
                            image[i][j] = black
                        else:
                            image[i][j] = white

            elif types == HAAR_FEATURE_TYPE_IV:
                for i in range(y, y + height*3):
                    for j in range(x, x + width):
                        if i >= (y + height) and i < (y + height * 2):
                            image[i][j] = black
                        else:
                            image[i][j] = white

            elif types == HAAR_FEATURE_TYPE_V:
                for i in range(y, y + height * 2):
                    for j in range(x, x + width * 2):
                        if (j < x + width and i < y + height) or\
                           (j >= x + width and i >= y + height):
                            image[i][j] = white
                        else:
                            image[i][j] = black
            else:
                raise Exception("Unkown type feature")

            #classifierPic += image * alpha * direction
            classifierPic += image


            pyplot.matshow(image, cmap = "gray")
            if DEBUG_MODEL == True:
                pylab.show()
            else:
                pyplot.savefig(FIGURES + "feature_" + str(n) + ".jpg")

        from image import Image
        classifierPic = Image._normalization(classifierPic)
        pylab.matshow(classifierPic, cmap = "gray")
        if DEBUG_MODEL == True:
            pylab.show()
        else:
            pyplot.savefig(FIGURES + "boosted_features.jpg")
