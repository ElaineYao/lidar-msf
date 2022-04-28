import csv
import matplotlib.pyplot as plt

def output1(path):  # return (detection rate, average score)
    num_line =[] # "----"
    with open(path, mode='r') as f:
        csvFile = csv.reader(f)
        idx = 0
        for row in csvFile:
            if row == ['----']:
                num_line.append(idx)
            # print(row)
            idx += 1
    # bg_num = []
    bg_line = [x+2 for x in num_line] # x,y,z parameters
    cnt_line = [x+1 for x in num_line] # num of objects
    bg = []
    cnt = [] 
    arr_line = []
    act_cnt = []
    act_score = []
    gnd = []
    # get the number of objects
    with open(path, mode='r') as f:
        csvFile = csv.reader(f)
        idx = 0
        for row in csvFile:
            if idx in cnt_line:
                cnt.append(int(row[0]))
            idx += 1
        # print(cnt)

    for i in range(len(cnt_line)):
        arr = (cnt_line[i]+2, cnt_line[i]+cnt[i]+1)
        arr_line.append(arr)
    # print(arr_line)

    with open(path, mode='r') as f:
        csvFile = csv.reader(f)
        idx = 0
        for row in csvFile:
            if idx in bg_line:
                # obj = row[3]
                bg_1 = row[4].split("/")
                bg_1 = bg_1[3].split(".")[0]
                bg_line.remove(idx)
                bg.append(int(bg_1))
            # print(bg)
                    
            # print(row)
            idx += 1

    # ground truth to be defined
    for item in bg:
        if(item == 1):
            gnd.append(4)
        elif(item == 2):
            gnd.append(2)
        elif(item == 3):
            gnd.append(9)
        elif(item == 4):
            gnd.append(4)


    for item in arr_line:
        ccnt = 0
        score = 0
        start = item[0]
        end = item[1]
        with open(path, mode='r') as f:
            csvFile = csv.reader(f)
            idx = 0
            for row in csvFile:
                if (idx>(start-1)) & (idx <(end+1)):
                    # print(row[0])
                    if(int(row[0]) == 2):
                        ccnt +=1
                        score +=float(row[1])
                if(idx >(end+1)):
                    continue
                idx +=1
        act_cnt.append(ccnt)
        act_score.append(score/ccnt)
    # print(act_score)
    # print(len(act_cnt))
    # print(len(bg))
    # print(act_cnt)
    # print(bg)

    zip_list = zip(act_cnt, gnd)
    d_rate = [x/y for (x,y) in zip_list]
    # print(d_rate)

    return d_rate, act_score    
        

                


    # print(num_line)

if __name__ == '__main__':
    output1_path = "./result/output1.csv"
    output2_path = "./result/output2.csv"
    d_rate1, act_score1 = output1(output1_path)
    d_rate2, act_score2 = output1(output2_path)

    delta_rate = [a - b for a, b in zip(d_rate1, d_rate2)]
    delta_score = [a - b for a, b in zip(act_score1, act_score2)] 

    for i in range(len(delta_rate)):
        if delta_rate[i] <0:
            print(i)
    print("---------")
    for i in range(len(delta_score)):
        if delta_score[i] <0:
            print(i)

    fig1 = plt.figure()
    plt.hist(d_rate1)  # density=False would make counts
    # plt.hist(d_rate1, density=True, bins=30)  # density=False would make counts
    plt.ylabel('Counts')
    plt.xlabel('Detection rate for benign objects')
    # plt.show()
    fig1.savefig('./figure/output1_det.png')
    
    fig2 = plt.figure()
    plt.hist(act_score1)  # density=False would make counts
    plt.ylabel('Counts')
    plt.xlabel('Confidence rate for benign objects')
    # plt.show()
    fig2.savefig('./figure/output1_score.png')

    fig3 = plt.figure()
    plt.hist(d_rate2)  # density=False would make counts
    # plt.hist(d_rate1, density=True, bins=30)  # density=False would make counts
    plt.ylabel('Counts')
    plt.xlabel('Detection rate for malicious objects')
    # plt.show()
    fig3.savefig('./figure/output2_det.png')
    
    fig4 = plt.figure()
    plt.hist(act_score2)  # density=False would make counts
    plt.ylabel('Counts')
    plt.xlabel('Confidence rate for malicious objects')
    # plt.show()
    fig4.savefig('./figure/output2_score.png')

    fig5 = plt.figure()
    plt.hist(delta_rate)  # density=False would make counts
    # plt.hist(d_rate1, density=True, bins=30)  # density=False would make counts
    plt.ylabel('Counts')
    plt.xlabel('Delta detection rate')
    # plt.show()
    fig5.savefig('./figure/delta_det.png')
    
    fig6 = plt.figure()
    plt.hist(delta_score)  # density=False would make counts
    plt.ylabel('Counts')
    plt.xlabel('Delta confidence rate')
    # plt.show()
    fig6.savefig('./figure/delta_score.png')




