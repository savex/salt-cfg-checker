# From dstremkovsky
"""```root@cfg01:/srv/salt/reclass# salt kvm01* net_checks.get_nics
kvm01.multinode-ha.int:
    |_
      - bond0
      - None
      - 00:25:90:e7:46:d0
      - 1
      - 1500
    |_
      - bond0.1306
      - None
      - 00:25:90:e7:46:d0
      - 1
      - 1500
    |_
      - enp2s0f0
      - None
      - 00:25:90:e7:46:d0
      - 1
      - 1500
    |_
      - enp2s0f1
      - None
      - 00:25:90:e7:46:d1
      - 0
      - 1500```

```Generate csv report for the env

.. code-block:: bash

   salt -C 'kvm* or cmp* or osd*' net_checks.get_nics_csv \
     | grep '^\ ' | sed 's/\ *//g' | grep -Ev ^server \
     | sed '1 i\server,nic_name,ip_addr,mac_addr,link,mtu,chassis_id,chassis_name,port_mac,port_descr'

**Example of system output:**

.. code-block:: bash

   server,nic_name,ip_addr,mac_addr,link,mtu,chassis_id,chassis_name,port_mac,port_descr
   cmp010.domain.com,bond0,None,b4:96:91:10:5b:3a,1,1500,,,,
   cmp010.domain.com,bond0.21,10.200.178.110,b4:96:91:10:5b:3a,1,1500,,,,
   cmp010.domain.com,bond0.22,10.200.179.110,b4:96:91:10:5b:3a,1,1500,,,,
   cmp010.domain.com,bond1,None,3c:fd:fe:34:ad:22,0,1500,,,,
   cmp010.domain.com,bond1.24,10.200.181.110,3c:fd:fe:34:ad:22,0,1500,,,,
   cmp010.domain.com,fourty5,None,3c:fd:fe:34:ad:20,0,9000,,,,
   cmp010.domain.com,fourty6,None,3c:fd:fe:34:ad:22,0,9000,,,,
   cmp010.domain.com,one1,None,b4:96:91:10:5b:38,0,1500,,,,
   cmp010.domain.com,one2,None,b4:96:91:10:5b:39,1,1500,f0:4b:3a:8f:75:40,exnfvaa18-20,548,ge-0/0/22
   cmp010.domain.com,one3,None,b4:96:91:10:5b:3a,1,1500,f0:4b:3a:8f:75:40,exnfvaa18-20,547,ge-0/0/21
   cmp010.domain.com,one4,10.200.177.110,b4:96:91:10:5b:3b,1,1500,f0:4b:3a:8f:75:40,exnfvaa18-20,546,ge-0/0/20
   cmp011.domain.com,bond0,None,b4:96:91:13:6c:aa,1,1500,,,,
   cmp011.domain.com,bond0.21,10.200.178.111,b4:96:91:13:6c:aa,1,1500,,,,
   cmp011.domain.com,bond0.22,10.200.179.111,b4:96:91:13:6c:aa,1,1500,,,,
   ...```
"""
