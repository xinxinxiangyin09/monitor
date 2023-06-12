-- creating database.
CREATE DATABASE `monitor` CHARACTER SET 'utf8mb4' COLLATE 'utf8mb4_general_ci';

-- creating tables.
SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS `connect_info`;
CREATE TABLE `connect_info`  (
  `id` int NOT NULL AUTO_INCREMENT,
  `ip_addr` varchar(15) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '主机IP',
  `port` int NOT NULL COMMENT 'SSH端口',
  `username` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT 'SSH用户名',
  `password` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT 'SSH密码',
  `listen_ports` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `is_true` int NOT NULL COMMENT '是否启用，0启用，1弃用',
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = Dynamic;

DROP TABLE IF EXISTS `server_info`;
CREATE TABLE `server_info`  (
  `id` int NOT NULL AUTO_INCREMENT,
  `host_id` int NOT NULL,
  `ip_status` int NOT NULL COMMENT 'IP通信状态',
  `ssh_status` int NOT NULL COMMENT 'SSH服务状态',
  `cpu_used` int NULL DEFAULT 0 COMMENT '正在运行的进程数',
  `cpu_count` int NULL DEFAULT 0 COMMENT '总进程数',
  `cpu_proportion` varchar(8) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '0' COMMENT 'CPU占用率',
  `memory_count` int NULL DEFAULT 0 COMMENT '总内存',
  `memory_used` int NULL DEFAULT 0 COMMENT '占用内存',
  `memory_proportion` varchar(8) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '0' COMMENT '内存占比',
  `disk_count` int NULL DEFAULT 0 COMMENT '硬盘总量',
  `disk_used` int NULL DEFAULT 0 COMMENT '硬盘使用量',
  `disk_proportion` int NULL DEFAULT 0 COMMENT '硬盘占用率',
  `disk_detail` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '硬盘详细信息',
  `ports_info` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '端口详细信息',
  `created` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '检测时间',
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `serverID_id`(`host_id` ASC) USING BTREE,
  CONSTRAINT `serverID_id` FOREIGN KEY (`host_id`) REFERENCES `connect_info` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = Dynamic;

SET FOREIGN_KEY_CHECKS = 1;

-- insert into data
INSERT INTO `connect_info` VALUES (1, '192.168.0.104', 22, 'root', '0', '21,22,3306,12306', 0);
INSERT INTO `connect_info` VALUES (2, '192.168.0.108', 22, 'root', '0', '6379,27017,12308', 0);

INSERT INTO `server_info` VALUES (1, 1, 1, 1, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '2023-06-10 03:43:18');
INSERT INTO `server_info` VALUES (2, 2, 0, 0, 3, 219, '1.0', 1016232, 821064, '81.0', 35345820, 4633080, 13, '[{\"path\": \"/dev/mapper/centos-root\", \"count_disk\": 13092864, \"used_disk\": 3549264, \"not_used_disk\": 9543600, \"proportion\": \"28%\"}, {\"path\": \"devtmpfs\", \"count_disk\": 497064, \"used_disk\": 0, \"not_used_disk\": 497064, \"proportion\": \"0%\"}, {\"path\": \"tmpfs\", \"count_disk\": 508116, \"used_disk\": 0, \"not_used_disk\": 508116, \"proportion\": \"0%\"}, {\"path\": \"tmpfs\", \"count_disk\": 508116, \"used_disk\": 6860, \"not_used_disk\": 501256, \"proportion\": \"2%\"}, {\"path\": \"tmpfs\", \"count_disk\": 508116, \"used_disk\": 0, \"not_used_disk\": 508116, \"proportion\": \"0%\"}, {\"path\": \"/dev/sdb1\", \"count_disk\": 19091584, \"used_disk\": 949560, \"not_used_disk\": 17165540, \"proportion\": \"6%\"}, {\"path\": \"/dev/sda1\", \"count_disk\": 1038336, \"used_disk\": 127396, \"not_used_disk\": 910940, \"proportion\": \"13%\"}, {\"path\": \"tmpfs\", \"count_disk\": 101624, \"used_disk\": 0, \"not_used_disk\": 101624, \"proportion\": \"0%\"}]', '[{\"port\": 6379, \"status\": \"closed\"}, {\"port\": 27017, \"status\": \"closed\"}, {\"port\": 12308, \"status\": \"listen\"}]', '2023-06-10 03:43:18');
